import logging
import os
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlmodel import Session

from app.db.session import get_session
from app.modules.alarms.api.interfaces import IAlarmsService, get_alarms_service
from app.modules.calendar.api.interfaces import ICalendarService, get_calendar_service
from app.modules.settings.api.interfaces import ISettingsService, get_settings_service
from app.modules.slideshow.api.interfaces import (
    ISlideshowService,
    get_slideshow_service,
)
from app.modules.weather.api.interfaces import IWeatherService, get_weather_service
from app.schemas import SlideResponse, WeatherResponse
from app.template_config import templates
from app.utils.timezone import datetime_to_iso_with_tz, ensure_utc_aware

router = APIRouter()
logger = logging.getLogger(__name__)


def require_debug_mode():
    """Dependency to protect debug endpoints - only accessible when WEBAPP_DEBUG is enabled."""
    debug_enabled = os.getenv("WEBAPP_DEBUG", "").lower() in ("true", "1", "yes")
    if not debug_enabled:
        raise HTTPException(status_code=404, detail="Not found")


def _isoformat_safe(dt_obj: object, tzid: str | None = None) -> str:
    """
    Return a timezone-aware ISO string for dt_obj or empty string on failure.

    If tzid is provided, the ISO string will include the timezone offset
    calculated from the original event timezone.
    """
    if not dt_obj or not hasattr(dt_obj, "isoformat"):
        return ""
    try:
        return datetime_to_iso_with_tz(ensure_utc_aware(dt_obj), tzid)
    except Exception:
        logger.debug("Failed to isoformat: %s", dt_obj)
        return ""


@router.get("/")
async def read_root(
    request: Request,
    session: Session = Depends(get_session),
    settings_service: ISettingsService = Depends(get_settings_service),
):
    """Modern Slideshow View"""
    user_agent = request.headers.get("user-agent", "").lower()
    logger.debug("Incoming User-Agent: %s", user_agent)

    # Auto-redirect for iPad 2 (iOS 9)
    # Broader check: "ipad" and "os 9" (case-insensitive)
    if "ipad" in user_agent and "os 9" in user_agent:
        return RedirectResponse(url="/legacy", status_code=302)

    settings = settings_service.get_settings(session)
    return templates.TemplateResponse(
        request, "index.html", {"mode": "modern", "settings": settings}
    )


@router.get("/legacy")
async def read_legacy(
    request: Request,
    session: Session = Depends(get_session),
    settings_service: ISettingsService = Depends(get_settings_service),
    calendar_service: ICalendarService = Depends(get_calendar_service),
):
    """Legacy Slideshow View (iPad 2)"""
    settings = settings_service.get_settings(session)
    # Determine the most recent calendar sync time (if any) to display in legacy UI
    try:
        statuses = await calendar_service.get_sync_status(session)
        latest = None
        for status_dict in statuses:
            if status_dict.get("last_synced_at") and (
                latest is None or status_dict["last_synced_at"] > latest
            ):
                latest = status_dict["last_synced_at"]
        last_sync_utc = ensure_utc_aware(latest).isoformat() if latest else ""
    except Exception:
        last_sync_utc = ""

    return templates.TemplateResponse(
        request,
        "legacy/index.html",
        {"mode": "legacy", "settings": settings, "last_sync_utc": last_sync_utc},
    )


@router.get("/components/weather", response_class=HTMLResponse, response_model=WeatherResponse)
async def get_weather(
    request: Request,
    session: Session = Depends(get_session),
    settings_service: ISettingsService = Depends(get_settings_service),
    weather_service: IWeatherService = Depends(get_weather_service),
):
    """
    Returns HTML fragment for weather widget.

    Renders the `partials/weather.html` template. The `WeatherResponse` model
    documents the structured weather data used by API consumers; the route
    itself renders HTML for the UI.
    """
    settings = settings_service.get_settings(session)

    if not settings or settings.weather_latitude is None or settings.weather_longitude is None:
        return templates.TemplateResponse(
            "partials/weather.html",
            {"request": request, "has_location": False},
        )

    lat = settings.weather_latitude
    lon = settings.weather_longitude

    weather_data = await weather_service.get_current_weather(lat, lon)
    weather = {
        "temp": weather_data.temp,
        "condition": weather_data.condition,
        "location": weather_data.location,
    }

    return templates.TemplateResponse(
        "partials/weather.html",
        {"request": request, "has_location": True, "weather": weather},
    )


@router.get("/components/slide", response_class=HTMLResponse, response_model=SlideResponse)
async def get_next_slide(
    request: Request,
    mode: str = "modern",
    session: Session = Depends(get_session),
    slideshow_service: ISlideshowService = Depends(get_slideshow_service),
):
    selection = slideshow_service.select_next_slide(session, mode)
    if selection.error_msg:
        return templates.TemplateResponse(
            "partials/slide.html",
            {"request": request, "error_msg": selection.error_msg},
        )

    return templates.TemplateResponse(
        "partials/slide.html",
        {"request": request, "img_url": selection.img_url},
    )


def _alarms_to_context(
    active_alarms: list[dict], mock: bool = False, tz_offset: int | None = None
) -> list[dict]:
    """Convert alarms into template-friendly context list."""
    from datetime import datetime as _datetime

    if not active_alarms:
        return []

    # Use a timezone-aware minimum datetime for sorting to avoid mixing naive/aware
    min_dt = _datetime.min.replace(tzinfo=UTC)

    def _sort_key(item: dict):
        dt = item.get("start")
        if not dt:
            return min_dt
        try:
            return ensure_utc_aware(dt)
        except Exception:
            # Fallback: if ensure fails, coerce naive to UTC
            try:
                return dt.replace(tzinfo=UTC)
            except Exception:
                return min_dt

    active_alarms.sort(key=_sort_key, reverse=True)

    tz_query = f"&tz_offset={tz_offset}" if tz_offset is not None else ""
    contexts: list[dict] = []
    for alarm in active_alarms:
        start_iso = ""
        end_iso = ""
        all_day = False
        tzid = alarm.get("tzid")
        start_iso = _isoformat_safe(alarm.get("start"), tzid)
        end_iso = _isoformat_safe(alarm.get("end"), tzid)
        if "all_day" in alarm:
            all_day = alarm["all_day"]

        fallback_text = _format_fallback_datetime(
            alarm.get("start"), alarm.get("end"), all_day, start_iso
        )

        contexts.append(
            {
                "uid": alarm.get("uid"),
                "name": alarm.get("name", ""),
                "fallback_text": fallback_text,
                "start_iso": start_iso,
                "end_iso": end_iso,
                "all_day": "true" if all_day else "false",
                "mock": mock,
                "tz_query": tz_query,
            }
        )

    return contexts


def _parse_alarm_id(alarm_id: str) -> tuple[object | None, int | None, str | None]:
    """Parse an alarm identifier which may be a UUID or a composite "source_id:event_uid".

    Returns: (alarm_uuid, calendar_source_id, calendar_event_uid)
    Raises: HTTPException(400) on invalid format.
    """
    from uuid import UUID

    calendar_source_id = None
    calendar_event_uid = None
    alarm_uuid = None

    # Try parsing as UUID first
    try:
        alarm_uuid = UUID(alarm_id)
        return alarm_uuid, None, None
    except ValueError:
        # Not a UUID - might be composite format "source_id:event_uid"
        if ":" in alarm_id:
            parts = alarm_id.split(":", 1)
            try:
                calendar_source_id = int(parts[0])
                calendar_event_uid = parts[1]
                # Validate calendar_event_uid format (allow timestamp chars: #, +, -, :, etc.)
                import re

                if not re.match(r"^[\w\-:.@#+]+$", calendar_event_uid):
                    raise HTTPException(status_code=400, detail="Invalid alarm ID format")
                if len(calendar_event_uid) > 500:
                    raise HTTPException(status_code=400, detail="Alarm ID too long")
                return None, calendar_source_id, calendar_event_uid
            except (ValueError, IndexError):
                raise HTTPException(status_code=400, detail="Invalid alarm ID format") from None
        else:
            raise HTTPException(status_code=400, detail="Invalid alarm ID format") from None


def _format_fallback_datetime(dt_obj, end_obj, all_day_flag: bool, start_iso_str: str) -> str:
    """Format a human-readable fallback string for an alarm datetime (French)."""
    try:
        if not dt_obj:
            return ""
        now_local = datetime.now(UTC)
        # Ensure start_dt is UTC-aware
        start_dt = (
            dt_obj if getattr(dt_obj, "tzinfo", None) is not None else dt_obj.replace(tzinfo=UTC)
        )

        days = [
            "Dimanche",
            "Lundi",
            "Mardi",
            "Mercredi",
            "Jeudi",
            "Vendredi",
            "Samedi",
        ]
        idx = start_dt.weekday() + 1 if start_dt.weekday() < 6 else 0
        month_names = [
            "janvier",
            "février",
            "mars",
            "avril",
            "mai",
            "juin",
            "juillet",
            "août",
            "septembre",
            "octobre",
            "novembre",
            "décembre",
        ]
        month = month_names[start_dt.month - 1]
        day_num = start_dt.day
        year_part = "" if start_dt.year == now_local.year else f" {start_dt.year}"
        day_text = f"{days[idx]}, {day_num} {month}{year_part}"

        if all_day_flag:
            return day_text

        def pad(n: int) -> str:
            return str(n).zfill(2)

        t1 = f"{pad(start_dt.hour)}:{pad(start_dt.minute)}"
        if end_obj:
            end_dt = end_obj if end_obj.tzinfo is not None else end_obj.replace(tzinfo=UTC)
            t2 = f"{pad(end_dt.hour)}:{pad(end_dt.minute)}"
            time_text = f"{t1}-{t2}" if t1 != t2 else t1
        else:
            time_text = t1

        return f"{day_text} {time_text}"
    except Exception as e:
        logger.debug("Failed to format fallback datetime: %s", e)
        return start_iso_str or ""


@router.get("/components/index-refresh", response_class=HTMLResponse)
async def components_index_refresh(
    request: Request,
    session: Session = Depends(get_session),
    settings_service: ISettingsService = Depends(get_settings_service),
    weather_service: IWeatherService = Depends(get_weather_service),
    alarms_service: IAlarmsService = Depends(get_alarms_service),
):
    """Return out-of-band fragments to refresh main index components.

    This endpoint returns HTML fragments with `hx-swap-oob` attributes so
    HTMX will update the corresponding wrappers on the client without
    replacing the triggering element.
    """
    settings = settings_service.get_settings(session)
    out_parts: list[str] = []

    # Weather fragment (if location configured)
    if (
        settings
        and settings.weather_latitude is not None
        and settings.weather_longitude is not None
    ):
        try:
            weather_data = await weather_service.get_current_weather(
                settings.weather_latitude, settings.weather_longitude
            )
            weather = {
                "temp": weather_data.temp,
                "condition": weather_data.condition,
                "location": weather_data.location,
            }
            weather_html = templates.env.get_template("partials/weather.html").render(
                request=request, has_location=True, weather=weather
            )
            out_parts.append(f'<div hx-swap-oob="innerHTML:#weather-wrapper">{weather_html}</div>')
        except Exception:
            logger.exception("Failed to render weather fragment for index-refresh")

    # Alarm fragment
    try:
        await alarms_service.purge_old_dismissed_alarms(session)
        active_alarms = await alarms_service.get_active_alarms(session)
        alarm_contexts = _alarms_to_context(active_alarms, mock=False, tz_offset=None)
        if alarm_contexts:
            alarm_html = templates.env.get_template("partials/alarms.html").render(
                alarms=alarm_contexts
            )
            out_parts.append(f'<div hx-swap-oob="innerHTML:#alarm-poller">{alarm_html}</div>')
        else:
            out_parts.append('<div hx-swap-oob="innerHTML:#alarm-poller"></div>')
    except Exception:
        logger.exception("Failed to render alarm fragment for index-refresh")

    return HTMLResponse("\n".join(out_parts))


@router.get("/components/alarm", response_class=HTMLResponse)
async def check_alarm(
    request: Request,
    mock: bool = False,
    tz_offset: int | None = None,
    session: Session = Depends(get_session),
    alarms_service: IAlarmsService = Depends(get_alarms_service),
):
    """Checks for active alarms and returns a list of them if any exist."""
    logger.info("Alarm refresh requested (mock=%s, tz_offset=%s)", mock, tz_offset)

    if mock:
        # Provide ISO datetimes so client-side can format using browser locale
        now = ensure_utc_aware(datetime.now())
        dt1 = now.replace(hour=14, minute=0, second=0, microsecond=0)
        dt2 = now.replace(hour=16, minute=30, second=0, microsecond=0)
        active_alarms = [
            {
                "uid": "mock-1",
                "name": "Meeting with Client",
                "start": dt1,
                "end": dt1 + timedelta(hours=1),
                "all_day": False,
            },
            {
                "uid": "mock-2",
                "name": "Dentist Appointment",
                "start": dt2,
                "end": dt2 + timedelta(hours=1),
                "all_day": False,
            },
            {
                "uid": "mock-3",
                "name": "Journée pédagogique",
                "start": now.replace(hour=0, minute=0, second=0, microsecond=0),
                "end": (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
                "all_day": True,
            },
        ]
    else:
        # Purge old alarms before fetching
        await alarms_service.purge_old_dismissed_alarms(session)
        # Fetch active alarms from service
        active_alarms = await alarms_service.get_active_alarms(session)

    # Convert to template context and render partial
    alarm_contexts = _alarms_to_context(active_alarms, mock, tz_offset)
    if not alarm_contexts:
        return HTMLResponse("")

    return templates.TemplateResponse(
        request,
        "partials/alarms.html",
        {"alarms": alarm_contexts},
    )


@router.get(
    "/debug/calendar-events",
    response_class=JSONResponse,
    dependencies=[Depends(require_debug_mode)],
)
async def debug_calendar_events(
    session: Session = Depends(get_session),
    alarms_service: IAlarmsService = Depends(get_alarms_service),
) -> JSONResponse:
    """Return cached calendar events and dismissed alarms for debugging."""
    debug_state = await alarms_service.get_debug_alarm_state(session)
    return JSONResponse(debug_state)


@router.get(
    "/debug/calendars",
    response_class=JSONResponse,
    dependencies=[Depends(require_debug_mode)],
)
async def debug_calendars(
    session: Session = Depends(get_session),
    calendar_service: ICalendarService = Depends(get_calendar_service),
) -> JSONResponse:
    """Return configured calendar sources and their sync status for debugging."""
    debug_state = await calendar_service.get_debug_calendar_state(session)
    return JSONResponse(debug_state)


@router.post("/api/alarms/{alarm_id}/dismiss", response_class=HTMLResponse)
async def dismiss_alarm(
    request: Request,
    alarm_id: str,
    mock: bool = False,
    tz_offset: int | None = None,
    session: Session = Depends(get_session),
    alarms_service: IAlarmsService = Depends(get_alarms_service),
):
    """Dismisses an alarm and returns the updated alarm list."""
    # If this is a mock request, bypass strict alarm_id validation and return
    # the mock alarm list immediately. Mock IDs (e.g. "mock-1") are allowed
    # and should not be treated as errors.
    if mock:
        return await check_alarm(
            request,
            mock=True,
            tz_offset=tz_offset,
            session=session,
            alarms_service=alarms_service,
        )

    # Use service to dismiss the alarm (handles UUID and composite UID parsing)
    await alarms_service.dismiss_alarm(alarm_id, session)

    # Return the updated list immediately
    logger.info("Alarm dismissed id=%s (tz_offset=%s)", alarm_id, tz_offset)
    return await check_alarm(
        request,
        mock=False,
        tz_offset=tz_offset,
        session=session,
        alarms_service=alarms_service,
    )

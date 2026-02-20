import logging
import os
import random
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.db.models import (
    AlarmEvent,
    AppSettings,
    CalendarEventCache,
    CalendarSource,
    CalendarSyncStatusEntry,
    Photo,
)
from app.db.session import get_session
from app.schemas import SlideResponse, WeatherResponse
from app.services.alarm_service import AlarmService
from app.services.weather_service import WeatherService
from app.utils.timezone import datetime_to_iso_with_tz, ensure_utc_aware

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
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
async def read_root(request: Request, session: Session = Depends(get_session)):
    """Modern Slideshow View"""
    user_agent = request.headers.get("user-agent", "").lower()
    logger.debug("Incoming User-Agent: %s", user_agent)

    # Auto-redirect for iPad 2 (iOS 9)
    # Broader check: "ipad" and "os 9" (case-insensitive)
    if "ipad" in user_agent and "os 9" in user_agent:
        return RedirectResponse(url="/legacy", status_code=302)

    settings = session.exec(select(AppSettings)).first()
    return templates.TemplateResponse(
        request, "index.html", {"mode": "modern", "settings": settings}
    )


@router.get("/legacy")
async def read_legacy(request: Request, session: Session = Depends(get_session)):
    """Legacy Slideshow View (iPad 2)"""
    settings = session.exec(select(AppSettings)).first()
    # Determine the most recent calendar sync time (if any) to display in legacy UI
    try:
        statuses = session.exec(select(CalendarSyncStatusEntry)).all()
        latest = None
        for st in statuses:
            if st.last_synced_at and (latest is None or st.last_synced_at > latest):
                latest = st.last_synced_at
        last_sync_utc = ensure_utc_aware(latest).isoformat() if latest else ""
    except Exception:
        last_sync_utc = ""

    return templates.TemplateResponse(
        request,
        "legacy/index.html",
        {"mode": "legacy", "settings": settings, "last_sync_utc": last_sync_utc},
    )


@router.get("/components/weather", response_class=HTMLResponse, response_model=WeatherResponse)
async def get_weather(request: Request, session: Session = Depends(get_session)):
    """
    Returns HTML fragment for weather widget.

    Renders the `partials/weather.html` template. The `WeatherResponse` model
    documents the structured weather data used by API consumers; the route
    itself renders HTML for the UI.
    """
    settings = session.exec(select(AppSettings)).first()

    if not settings or settings.weather_latitude is None or settings.weather_longitude is None:
        return templates.TemplateResponse(
            "partials/weather.html",
            {"request": request, "has_location": False},
        )

    lat = settings.weather_latitude
    lon = settings.weather_longitude

    weather = await WeatherService.get_current_weather(lat, lon)

    return templates.TemplateResponse(
        "partials/weather.html",
        {"request": request, "has_location": True, "weather": weather},
    )


@router.get("/components/slide", response_class=HTMLResponse, response_model=SlideResponse)
async def get_next_slide(
    request: Request, mode: str = "modern", session: Session = Depends(get_session)
):
    settings = session.exec(select(AppSettings)).first()
    if not settings or settings.active_preset_id is None:
        return templates.TemplateResponse(
            "partials/slide.html",
            {"request": request, "error_msg": "No Preset Active. Please configure in Admin."},
        )

    photos = session.exec(select(Photo).where(Photo.preset_id == settings.active_preset_id)).all()

    if not photos:
        return templates.TemplateResponse(
            "partials/slide.html",
            {"request": request, "error_msg": "No Photos found in the active preset."},
        )

    photo = random.choice(photos)
    img_url = f"/images/{photo.id}?mode={mode}"

    return templates.TemplateResponse(
        "partials/slide.html",
        {"request": request, "img_url": img_url},
    )


# Alarm formatting and purge logic moved to AlarmService in app/services/alarm_service.py


async def _fetch_calendar_alarms(session: Session, _tz_offset: int | None = None) -> list[dict]:
    """Fetch alarms from cached calendar events and filter dismissed ones."""
    # Use CalendarService.get_upcoming_alarms to get alarms with correct trigger_time
    utc_now = datetime.now(UTC)
    window_start = utc_now - timedelta(days=7)
    window_end = utc_now + timedelta(days=7)
    # For each calendar source, aggregate events in window
    sources = session.exec(select(CalendarSource)).all()
    active_alarms: list[dict] = []
    for source in sources:
        cached_events = session.exec(
            select(CalendarEventCache).where(
                (CalendarEventCache.calendar_source_id == source.id)
                & (CalendarEventCache.event_start <= window_end)
                & (CalendarEventCache.event_end >= window_start)
            )
        ).all()

        for event in cached_events:
            # Determine effective trigger time (fallback to event_start)
            trigger = (
                event.trigger_time
                if hasattr(event, "trigger_time") and event.trigger_time is not None
                else event.event_start
            )

            # Normalize trigger to UTC-aware for safe comparisons
            try:
                trigger_aware = ensure_utc_aware(trigger) if trigger is not None else None
            except Exception:
                if trigger is None:
                    continue
                trigger_aware = (
                    trigger
                    if getattr(trigger, "tzinfo", None) is not None
                    else trigger.replace(tzinfo=UTC)
                )

            # Only show alarms when their trigger_time has been reached
            if trigger_aware is None or trigger_aware > utc_now:
                continue

            composite_uid = f"{event.calendar_source_id}:{event.uid}"

            # Check if alarm was dismissed using calendar relationship
            dismissed = session.exec(
                select(AlarmEvent).where(
                    AlarmEvent.calendar_source_id == event.calendar_source_id,
                    AlarmEvent.calendar_event_uid == event.uid,
                )
            ).first()

            if not dismissed or dismissed.dismissed_at is None:
                alarm = {
                    "uid": composite_uid,
                    "name": event.summary,
                    "start": event.event_start,
                    "end": event.event_end,
                    "tzid": getattr(event, "event_tz", None),
                    "all_day": (
                        event.event_start.hour == 0
                        and event.event_start.minute == 0
                        and (event.event_end - event.event_start).days >= 1
                    ),
                    "trigger_time": trigger,
                }
                active_alarms.append(alarm)

    return active_alarms


def _fetch_simulated_alarms(session: Session) -> list[dict]:
    """Fetch test/simulated alarms from database."""
    # Use naive UTC datetime for DB comparison (SQLite stores datetimes as naive)
    now_naive = datetime.now(UTC).replace(tzinfo=None)

    # Test alarms have no calendar link (NULL calendar_source_id)
    simulated_alarms = session.exec(
        select(AlarmEvent).where(
            (AlarmEvent.calendar_source_id.is_(None))  # type: ignore[attr-defined,union-attr]
            & (AlarmEvent.trigger_time <= now_naive)
            & (AlarmEvent.dismissed_at.is_(None))  # type: ignore[attr-defined,union-attr]
        )
    ).all()

    alarms = []
    for alarm_event in simulated_alarms:
        # Ensure trigger_time is timezone-aware (DB may contain legacy naive datetimes)
        try:
            start_dt = ensure_utc_aware(alarm_event.trigger_time)
        except Exception:
            start_dt = alarm_event.trigger_time

        try:
            end_dt = ensure_utc_aware(alarm_event.trigger_time + timedelta(hours=1))
        except Exception:
            end_dt = alarm_event.trigger_time + timedelta(hours=1)

        alarms.append(
            {
                "uid": str(alarm_event.id),  # Use UUID as uid for backwards compatibility
                "name": "Simulated Event",
                "start": start_dt,
                "end": end_dt,
                "all_day": False,
                # Don't specify tzid - let frontend/browser handle timezone conversion from UTC
            }
        )
    return alarms


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


def _render_alarms_html(
    active_alarms: list[dict], mock: bool = False, tz_offset: int | None = None
) -> str:
    """Generate HTML for alarm list (backwards-compatible helper used in tests)."""
    if not active_alarms:
        return ""

    from datetime import datetime as _datetime

    # Use timezone-aware minimum datetime for sorting
    min_dt = _datetime.min.replace(tzinfo=UTC)

    def _sort_key(item: dict):
        dt = item.get("start")
        if not dt:
            return min_dt
        try:
            return ensure_utc_aware(dt)
        except Exception:
            try:
                return dt.replace(tzinfo=UTC)
            except Exception:
                return min_dt

    active_alarms.sort(key=_sort_key, reverse=True)

    tz_query = f"&tz_offset={tz_offset}" if tz_offset is not None else ""
    alarms_html = ""
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

        alarms_html += _render_alarm_item(
            alarm, fallback_text, start_iso, end_iso, all_day, mock, tz_query
        )

    return f"""
    <div id="alarm-box" class="alarm-box-container">
        {alarms_html}
    </div>
    """


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


def _render_alarm_item(
    alarm: dict,
    fallback_text: str,
    start_iso: str,
    end_iso: str,
    all_day: bool,
    mock: bool,
    tz_query: str,
) -> str:
    """Render a single alarm item HTML snippet."""
    from markupsafe import escape

    uid = alarm.get("uid")
    name = alarm.get("name", "")
    # Security: Escape HTML to prevent XSS attacks from calendar event summaries
    escaped_name = escape(name)
    escaped_fallback = escape(fallback_text)
    return f"""
        <div class="alarm-item">
            <div class="alarm-header">
                <span class="alarm-icon">📅</span>
                <span class="alarm-title">{escaped_name}</span>
            </div>
            <div class="alarm-body">
                <span class="alarm-time alarm-time-small" data-start="{start_iso}" data-end="{end_iso}" data-allday="{str(all_day).lower()}">{escaped_fallback}</span>
            </div>
            <button hx-post="/api/alarms/{uid}/dismiss?mock={"true" if mock else "false"}{tz_query}"
                    hx-target="#alarm-poller"
                    hx-swap="innerHTML"
                    class="dismiss-btn-small">Dismiss</button>
        </div>
        """


@router.get("/components/index-refresh", response_class=HTMLResponse)
async def components_index_refresh(request: Request, session: Session = Depends(get_session)):
    """Return out-of-band fragments to refresh main index components.

    This endpoint returns HTML fragments with `hx-swap-oob` attributes so
    HTMX will update the corresponding wrappers on the client without
    replacing the triggering element.
    """
    settings = session.exec(select(AppSettings)).first()
    out_parts: list[str] = []

    # Weather fragment (if location configured)
    if (
        settings
        and settings.weather_latitude is not None
        and settings.weather_longitude is not None
    ):
        try:
            weather = await WeatherService.get_current_weather(
                settings.weather_latitude, settings.weather_longitude
            )
            weather_html = templates.env.get_template("partials/weather.html").render(
                request=request, has_location=True, weather=weather
            )
            out_parts.append(f'<div hx-swap-oob="innerHTML:#weather-wrapper">{weather_html}</div>')
        except Exception:
            logger.exception("Failed to render weather fragment for index-refresh")

    # Alarm fragment
    try:
        AlarmService.purge_old_dismissed_alarms(session)
        calendar_alarms = await _fetch_calendar_alarms(session, None)
        simulated_alarms = _fetch_simulated_alarms(session)
        active_alarms = calendar_alarms + simulated_alarms
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
):
    """Checks for active alarms and returns a list of them if any exist."""
    logger.info("Alarm refresh requested (mock=%s, tz_offset=%s)", mock, tz_offset)
    AlarmService.purge_old_dismissed_alarms(session)

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
        # Fetch real alarms from calendars and simulated alarms
        calendar_alarms = await _fetch_calendar_alarms(session, tz_offset)
        simulated_alarms = _fetch_simulated_alarms(session)
        active_alarms = calendar_alarms + simulated_alarms

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
async def debug_calendar_events(session: Session = Depends(get_session)) -> JSONResponse:
    """Return cached calendar events and dismissed alarms for debugging."""
    cached = session.exec(select(CalendarEventCache)).all()
    alarms = session.exec(select(AlarmEvent)).all()

    events_out = []
    for ev in cached:
        try:
            start_iso = ensure_utc_aware(ev.event_start).isoformat() if ev.event_start else None
        except Exception:
            start_iso = ev.event_start.isoformat() if ev.event_start else None
        try:
            end_iso = ensure_utc_aware(ev.event_end).isoformat() if ev.event_end else None
        except Exception:
            end_iso = ev.event_end.isoformat() if ev.event_end else None
        events_out.append(
            {
                "calendar_source_id": ev.calendar_source_id,
                "uid": ev.uid,
                "start": start_iso,
                "end": end_iso,
                "summary": ev.summary,
                "tzid": getattr(ev, "event_tz", None),
            }
        )

    alarms_out = []
    for a in alarms:
        try:
            trig_iso = ensure_utc_aware(a.trigger_time).isoformat() if a.trigger_time else None
        except Exception:
            trig_iso = a.trigger_time.isoformat() if a.trigger_time else None
        try:
            dismissed_iso = ensure_utc_aware(a.dismissed_at).isoformat() if a.dismissed_at else None
        except Exception:
            dismissed_iso = a.dismissed_at.isoformat() if a.dismissed_at else None
        alarms_out.append(
            {
                "id": str(a.id),  # Convert UUID to string
                "calendar_source_id": a.calendar_source_id,
                "calendar_event_uid": a.calendar_event_uid,
                "trigger_time": trig_iso,
                "dismissed_at": dismissed_iso,
            }
        )

    return JSONResponse({"cached_events": events_out, "alarm_events": alarms_out})


@router.get(
    "/debug/calendars", response_class=JSONResponse, dependencies=[Depends(require_debug_mode)]
)
async def debug_calendars(session: Session = Depends(get_session)) -> JSONResponse:
    """Return configured calendar sources and their sync status for debugging."""
    sources = session.exec(select(CalendarSource)).all()
    statuses = session.exec(select(CalendarSyncStatusEntry)).all()

    src_out = [{"id": s.id, "label": s.label, "url": s.url} for s in sources]

    status_out = []
    for st in statuses:
        try:
            last_iso = (
                ensure_utc_aware(st.last_synced_at).isoformat() if st.last_synced_at else None
            )
        except Exception:
            last_iso = st.last_synced_at.isoformat() if st.last_synced_at else None
        try:
            next_iso = ensure_utc_aware(st.next_sync_at).isoformat() if st.next_sync_at else None
        except Exception:
            next_iso = st.next_sync_at.isoformat() if st.next_sync_at else None
        status_out.append(
            {
                "calendar_source_id": st.calendar_source_id,
                "last_synced_at": last_iso,
                "next_sync_at": next_iso,
                "sync_status": st.sync_status,
                "error_message": st.error_message,
                "error_count": st.error_count,
            }
        )

    return JSONResponse({"sources": src_out, "statuses": status_out})


@router.post("/api/alarms/{alarm_id}/dismiss", response_class=HTMLResponse)
async def dismiss_alarm(
    request: Request,
    alarm_id: str,
    mock: bool = False,
    tz_offset: int | None = None,
    session: Session = Depends(get_session),
):
    """Dismisses an alarm and returns the updated alarm list."""
    from uuid import uuid4

    # Parse alarm_id - could be UUID or composite uid (calendar_source_id:event_uid)
    calendar_source_id = None
    calendar_event_uid = None
    alarm_uuid = None

    # If this is a mock request, bypass strict alarm_id validation and return
    # the mock alarm list immediately. Mock IDs (e.g. "mock-1") are allowed
    # and should not be treated as errors.
    if mock:
        return await check_alarm(request, mock=True, tz_offset=tz_offset, session=session)

    # Parse alarm_id into components
    alarm_uuid, calendar_source_id, calendar_event_uid = _parse_alarm_id(alarm_id)

    if not mock:
        existing = None

        if alarm_uuid:
            # Direct UUID lookup
            existing = session.exec(select(AlarmEvent).where(AlarmEvent.id == alarm_uuid)).first()
        else:
            # Lookup by calendar relationship
            existing = session.exec(
                select(AlarmEvent).where(
                    AlarmEvent.calendar_source_id == calendar_source_id,
                    AlarmEvent.calendar_event_uid == calendar_event_uid,
                )
            ).first()

        if existing:
            # Update existing alarm record with dismissal time (UTC-aware)
            existing.dismissed_at = ensure_utc_aware(datetime.now())
            session.add(existing)
        else:
            # Create new alarm record for calendar event dismissal
            trigger_time = ensure_utc_aware(datetime.now())

            # Try to find cached event for accurate trigger time
            if calendar_source_id and calendar_event_uid:
                try:
                    cached = session.exec(
                        select(CalendarEventCache).where(
                            CalendarEventCache.calendar_source_id == calendar_source_id,
                            CalendarEventCache.uid == calendar_event_uid,
                        )
                    ).first()
                    if cached:
                        trigger_time = cached.event_start
                except Exception as e:
                    logger.exception(
                        "DB lookup error while finding cached event for calendar_source_id=%s, uid=%s: %s",
                        calendar_source_id,
                        calendar_event_uid,
                        e,
                    )
                    # Fall back to now on any DB lookup error
                    trigger_time = ensure_utc_aware(datetime.now())

            alarm_event = AlarmEvent(
                id=uuid4(),  # Generate new UUID
                trigger_time=trigger_time,
                dismissed_at=ensure_utc_aware(datetime.now()),
                calendar_source_id=calendar_source_id,
                calendar_event_uid=calendar_event_uid,
            )
            session.add(alarm_event)

        session.commit()
        # Refresh session to ensure we get updated data
        session.expunge_all()

    # Return the updated list immediately
    logger.info("Alarm dismissed id=%s (mock=%s, tz_offset=%s)", alarm_id, mock, tz_offset)
    return await check_alarm(request, mock=mock, tz_offset=tz_offset, session=session)

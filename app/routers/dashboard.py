import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.modules.alarms.api import render_alarms_fragment
from app.modules.alarms.api.interfaces import IAlarmsService, get_alarms_service
from app.modules.calendar.api.interfaces import ICalendarService, get_calendar_service
from app.modules.settings.api.interfaces import ISettingsService, get_settings_service
from app.modules.slideshow.api import render_slide_fragment
from app.modules.slideshow.api.interfaces import (
    ISlideshowService,
    get_slideshow_service,
)
from app.modules.weather.api import render_weather_fragment
from app.modules.weather.api.interfaces import IWeatherService, get_weather_service
from app.schemas import SlideResponse, WeatherResponse
from app.template_config import templates

router = APIRouter()
logger = logging.getLogger(__name__)


def require_debug_mode():
    """Dependency to protect debug endpoints - only accessible when WEBAPP_DEBUG is enabled."""
    debug_enabled = os.getenv("WEBAPP_DEBUG", "").lower() in ("true", "1", "yes")
    if not debug_enabled:
        raise HTTPException(status_code=404, detail="Not found")


@router.get("/")
async def read_root(
    request: Request,
    settings_service: ISettingsService = Depends(get_settings_service),
):
    """Modern Slideshow View"""
    user_agent = request.headers.get("user-agent", "").lower()
    logger.debug("Incoming User-Agent: %s", user_agent)

    # Auto-redirect for iPad 2 (iOS 9)
    # Broader check: "ipad" and "os 9" (case-insensitive)
    if "ipad" in user_agent and "os 9" in user_agent:
        return RedirectResponse(url="/legacy", status_code=302)

    settings = settings_service.get_settings()
    tpl = templates.env.get_template("index.html")
    return HTMLResponse(tpl.render(request=request, mode="modern", settings=settings))


@router.get("/legacy")
async def read_legacy(
    request: Request,
    settings_service: ISettingsService = Depends(get_settings_service),
    calendar_service: ICalendarService = Depends(get_calendar_service),
):
    """Legacy Slideshow View (iPad 2 compatibility).

    Renders the older slideshow UI used by iPad 2 clients that require
    a simplified template and polling behaviour.
    """
    settings = settings_service.get_settings()
    last_sync_utc = await calendar_service.get_latest_sync_utc_iso()

    tpl = templates.env.get_template("legacy/index.html")
    return HTMLResponse(
        tpl.render(request=request, mode="legacy", settings=settings, last_sync_utc=last_sync_utc)
    )


@router.get("/components/weather", response_class=HTMLResponse, response_model=WeatherResponse)
async def get_weather(
    request: Request,  # noqa: ARG001
    settings_service: ISettingsService = Depends(get_settings_service),
    weather_service: IWeatherService = Depends(get_weather_service),
):
    """
    Returns HTML fragment for weather widget.

    Renders the `partials/weather.html` template. The `WeatherResponse` model
    documents the structured weather data used by API consumers; the route
    itself renders HTML for the UI.
    """
    settings = settings_service.get_settings()

    lat = settings.weather_latitude if settings else None
    lon = settings.weather_longitude if settings else None

    if lat is None or lon is None:
        return HTMLResponse(render_weather_fragment(has_location=False))

    weather_data = await weather_service.get_current_weather(lat, lon)
    weather_payload = {
        "temp": weather_data.temp,
        "condition": weather_data.condition,
        "location": weather_data.location,
    }
    return HTMLResponse(render_weather_fragment(has_location=True, weather=weather_payload))


@router.get("/components/slide", response_class=HTMLResponse, response_model=SlideResponse)
async def get_next_slide(
    request: Request,  # noqa: ARG001
    mode: str = "modern",
    slideshow_service: ISlideshowService = Depends(get_slideshow_service),
):
    selection = slideshow_service.select_next_slide(mode)
    return HTMLResponse(
        render_slide_fragment(img_url=selection.img_url, error_msg=selection.error_msg)
    )


@router.get("/components/index-refresh", response_class=HTMLResponse)
async def components_index_refresh(
    request: Request,  # noqa: ARG001
    settings_service: ISettingsService = Depends(get_settings_service),
    weather_service: IWeatherService = Depends(get_weather_service),
):
    """Return out-of-band fragments to refresh weather-related index components.

    This endpoint returns HTML fragments with `hx-swap-oob` attributes so
    HTMX will update the corresponding wrappers on the client without
    replacing the triggering element.
    """
    settings = settings_service.get_settings()
    out_parts: list[str] = []

    # Weather fragment (if location configured)
    if (
        settings
        and settings.weather_latitude is not None
        and settings.weather_longitude is not None
    ):
        try:
            weather_data = await weather_service.get_current_weather(
                settings.weather_latitude,
                settings.weather_longitude,
            )
            weather_payload = {
                "temp": weather_data.temp,
                "condition": weather_data.condition,
                "location": weather_data.location,
            }
            weather_html = render_weather_fragment(has_location=True, weather=weather_payload)
            out_parts.append(f'<div hx-swap-oob="innerHTML:#weather-wrapper">{weather_html}</div>')
        except Exception:
            logger.exception("Failed to render weather fragment for index-refresh")

    return HTMLResponse("\n".join(out_parts))


@router.get("/components/alarm", response_class=HTMLResponse)
async def check_alarm(
    request: Request,  # noqa: ARG001
    mock: bool = False,
    tz_offset: int | None = None,
    alarms_service: IAlarmsService = Depends(get_alarms_service),
):
    """Checks for active alarms and returns a list of them if any exist."""
    logger.info("Alarm refresh requested (mock=%s, tz_offset=%s)", mock, tz_offset)

    alarm_contexts = await alarms_service.get_alarm_contexts(mock=mock, tz_offset=tz_offset)
    return HTMLResponse(render_alarms_fragment(alarm_contexts))


@router.get(
    "/debug/calendar-events",
    response_class=JSONResponse,
    dependencies=[Depends(require_debug_mode)],
)
async def debug_calendar_events(
    alarms_service: IAlarmsService = Depends(get_alarms_service),
) -> JSONResponse:
    """Return cached calendar events and dismissed alarms for debugging."""
    debug_state = await alarms_service.get_debug_alarm_state()
    return JSONResponse(debug_state)


@router.get(
    "/debug/calendars",
    response_class=JSONResponse,
    dependencies=[Depends(require_debug_mode)],
)
async def debug_calendars(
    calendar_service: ICalendarService = Depends(get_calendar_service),
) -> JSONResponse:
    """Return configured calendar sources and their sync status for debugging."""
    debug_state = await calendar_service.get_debug_calendar_state()
    return JSONResponse(debug_state)


@router.post("/api/alarms/{alarm_id}/dismiss", response_class=HTMLResponse)
async def dismiss_alarm(
    request: Request,  # noqa: ARG001
    alarm_id: str,  # noqa: ARG001
):
    raise HTTPException(
        status_code=410,
        detail=(
            "Deprecated alarm mutation route. Use POST /api/v1/alarms/{alarm_id}/dismiss "
            "and refresh /components/alarm."
        ),
    )

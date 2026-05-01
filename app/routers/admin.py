import contextlib
import logging
import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse

from app.modules.alarms.api.interfaces import IAlarmsService, get_alarms_service
from app.modules.calendar.api.interfaces import ICalendarService, get_calendar_service
from app.modules.media.api.interfaces import IMediaService, get_media_service
from app.modules.settings.api.exceptions import PresetNotFoundError
from app.modules.settings.api.interfaces import ISettingsService, get_settings_service
from app.modules.weather.api.interfaces import IWeatherService, get_weather_service
from app.template_config import templates
from app.utils.timezone import get_local_timezone_name

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)


# --- Main Shell ---
@router.get("/")
async def admin_shell(request: Request):
    """Admin Shell with Sidebar"""
    debug_mode = os.getenv("WEBAPP_DEBUG", "").lower() in ("true", "1", "yes")
    tpl = templates.env.get_template("admin_base.html")
    return HTMLResponse(tpl.render(request=request, debug_mode=debug_mode))


# --- Partials: Settings ---
@router.get("/partials/settings", response_class=HTMLResponse)
async def get_settings_partial(
    request: Request,  # noqa: ARG001
    settings_service: ISettingsService = Depends(get_settings_service),
    weather_service: IWeatherService = Depends(get_weather_service),
):
    settings = settings_service.get_settings_form()
    location_name = await weather_service.get_location_name(
        settings.weather_latitude,
        settings.weather_longitude,
    )
    return HTMLResponse(
        settings_service.get_settings_html(
            location_name=location_name,
            backend_timezone=get_local_timezone_name(),
            form=settings,
        )
    )


@router.post("/settings/search", response_class=HTMLResponse)
async def search_location(
    request: Request,  # noqa: ARG001
    location_query: str = Form(...),
    settings_service: ISettingsService = Depends(get_settings_service),
    weather_service: IWeatherService = Depends(get_weather_service),
):
    """
    Geocodes the location query and returns the settings form
    pre-filled with the new coordinates (not saved yet).
    """
    settings = settings_service.get_settings_form()

    lat, lon, location_name = await weather_service.geocode_for_settings(location_query)
    if lat is not None and lon is not None:
        settings = settings_service.with_location_preview(settings, lat, lon)

    return HTMLResponse(
        settings_service.get_settings_html(
            location_name=location_name,
            backend_timezone=get_local_timezone_name(),
            form=settings,
        )
    )


@router.post("/settings", response_class=HTMLResponse)
async def update_settings(
    request: Request,  # noqa: ARG001
    active_preset_id: int | None = Form(None),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    duration: int | None = Form(None),
    default_alarm_for_all_events: str | None = Form(None),
    settings_service: ISettingsService = Depends(get_settings_service),
):
    try:
        settings_service.validate_settings_input(latitude, longitude, duration)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        settings_service.save_settings(
            active_preset_id=active_preset_id,
            latitude=latitude,
            longitude=longitude,
            duration=duration,
            default_alarm_for_all_events=default_alarm_for_all_events is not None,
        )
    except PresetNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Redirect to the main slideshow using HTMX
    response = HTMLResponse()
    response.headers["HX-Redirect"] = "/"
    return response


# --- Partials: Calendars ---
@router.get("/partials/calendars", response_class=HTMLResponse)
async def get_calendars_partial(
    request: Request,  # noqa: ARG001
    calendar_service: ICalendarService = Depends(get_calendar_service),
):
    return HTMLResponse(await calendar_service.get_calendars_html())


@router.post("/calendars", response_class=HTMLResponse)
async def add_calendar(
    request: Request,
    calendar_service: ICalendarService = Depends(get_calendar_service),
):
    """Manually trigger calendar synchronization."""

    # Run sync inline so the HTMX request only returns when sync completes.
    # This gives users visible feedback (loading indicator) matching
    # actual work. Run sync but suppress exceptions to avoid bubbling
    # errors to the admin UI
    with contextlib.suppress(Exception):
        await calendar_service.sync_calendars()

    return await get_calendars_partial(request, calendar_service)


# --- Partials: Gallery ---
@router.get("/partials/gallery", response_class=HTMLResponse)
async def get_gallery_partial(
    request: Request,  # noqa: ARG001
    preset_id: int | None = None,
    media_service: IMediaService = Depends(get_media_service),
):
    return HTMLResponse(await media_service.get_gallery_html(preset_id=preset_id))


@router.post("/presets", response_class=HTMLResponse)
async def create_preset(
    request: Request,
    name: str = Form(...),
    media_service: IMediaService = Depends(get_media_service),
):
    await media_service.create_preset(name)
    # Refresh gallery showing new preset
    return await get_gallery_partial(request, None, media_service)


@router.post("/upload", response_class=HTMLResponse)
async def upload_photos(
    request: Request,  # noqa: ARG001
    preset_id: int = Form(...),
    files: list[UploadFile] = File(...),
    media_service: IMediaService = Depends(get_media_service),
):
    try:
        await media_service.upload_photos(preset_id, files)
    except ValueError as ve:
        return HTMLResponse(
            await media_service.get_gallery_html(
                preset_id=preset_id,
                error_message=str(ve),
            )
        )

    return HTMLResponse(await media_service.get_gallery_html(preset_id=preset_id))


@router.delete("/photos/{photo_id}", response_class=HTMLResponse)
async def delete_photo(
    request: Request,
    photo_id: int,
    media_service: IMediaService = Depends(get_media_service),
):
    photo = await media_service.get_photo_by_id(photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    preset_id = photo.preset_id
    await media_service.delete_photo_from_db(photo_id)

    return await get_gallery_partial(request, preset_id, media_service)


# --- Debug Panel ---
@router.get("/partials/debug", response_class=HTMLResponse)
async def get_debug_partial(
    request: Request,  # noqa: ARG001
    alarms_service: IAlarmsService = Depends(get_alarms_service),
):
    """Debug control panel for testing (HTMX partial)."""
    return HTMLResponse(await alarms_service.get_debug_html())


@router.post("/debug/simulate-alarm", response_class=HTMLResponse)
async def simulate_alarm(
    request: Request,  # noqa: ARG001
    delay_seconds: int = Form(...),
    alarms_service: IAlarmsService = Depends(get_alarms_service),
):
    """Create a simulated alarm that appears after the specified delay."""
    await alarms_service.create_simulated_alarm(delay_seconds)
    return HTMLResponse(
        await alarms_service.get_debug_html(
            success_message=(f"Simulated alarm created! It will appear in {delay_seconds} seconds.")
        )
    )

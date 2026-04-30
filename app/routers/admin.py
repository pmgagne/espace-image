import contextlib
import logging
import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from app.db.models import (
    AppSettings,
)
from app.db.session import get_session
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
    return templates.TemplateResponse(request, "admin_base.html", {"debug_mode": debug_mode})


# --- Partials: Settings ---
@router.get("/partials/settings", response_class=HTMLResponse)
async def get_settings_partial(
    request: Request,
    session: Session = Depends(get_session),
    settings_service: ISettingsService = Depends(get_settings_service),
    weather_service: IWeatherService = Depends(get_weather_service),
):
    settings = settings_service.get_settings(session)
    presets = settings_service.list_presets(session)

    location_name = ""
    if settings and settings.weather_latitude and settings.weather_longitude:
        try:
            location_name = (
                await weather_service.reverse_geocode(
                    settings.weather_latitude,
                    settings.weather_longitude,
                )
                or ""
            )
        except Exception:
            logger.exception("Geocoding error while reverse geocoding")

    backend_timezone = get_local_timezone_name()

    return templates.TemplateResponse(
        request,
        "partials/settings.html",
        {
            "settings": settings,
            "presets": presets,
            "location_name": location_name,
            "backend_timezone": backend_timezone,
        },
    )


@router.post("/settings/search", response_class=HTMLResponse)
async def search_location(
    request: Request,
    location_query: str = Form(...),
    session: Session = Depends(get_session),
    settings_service: ISettingsService = Depends(get_settings_service),
    weather_service: IWeatherService = Depends(get_weather_service),
):
    """
    Geocodes the location query and returns the settings form
    pre-filled with the new coordinates (not saved yet).
    """
    settings = settings_service.get_settings(session)
    if not settings:
        settings = AppSettings()

    presets = settings_service.list_presets(session)

    # Perform Geocoding
    result_data = await weather_service.geocode_location(location_query)
    result = None
    if result_data is not None:
        result = {
            "lat": result_data.lat,
            "lon": result_data.lon,
            "name": result_data.name,
        }
    location_name = "Location not found"

    if result:
        # Update the settings object in memory only (no commit)
        settings.weather_latitude = result["lat"]
        settings.weather_longitude = result["lon"]
        location_name = result["name"]

    return templates.TemplateResponse(
        request,
        "partials/settings.html",
        {
            "settings": settings,
            "presets": presets,
            "location_name": location_name,
            "backend_timezone": get_local_timezone_name(),
        },
    )


@router.post("/settings", response_class=HTMLResponse)
async def update_settings(
    request: Request,  # noqa: ARG001
    active_preset_id: int | None = Form(None),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    duration: int | None = Form(None),
    default_alarm_for_all_events: str | None = Form(None),
    session: Session = Depends(get_session),
    settings_service: ISettingsService = Depends(get_settings_service),
):
    # Basic validation for form inputs
    import math

    if latitude is not None and (
        math.isnan(latitude) or math.isinf(latitude) or not (-90.0 <= latitude <= 90.0)
    ):
        raise HTTPException(status_code=422, detail="Invalid latitude value")
    if longitude is not None and (
        math.isnan(longitude) or math.isinf(longitude) or not (-180.0 <= longitude <= 180.0)
    ):
        raise HTTPException(status_code=422, detail="Invalid longitude value")
    if duration is not None and duration <= 0:
        raise HTTPException(status_code=422, detail="Duration must be a positive integer")

    try:
        settings_service.save_settings(
            session=session,
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
    request: Request,
    session: Session = Depends(get_session),
    calendar_service: ICalendarService = Depends(get_calendar_service),
):
    data = await calendar_service.get_calendars_for_ui(session)
    return templates.TemplateResponse(
        request,
        "partials/calendars.html",
        data,
    )


@router.post("/calendars", response_class=HTMLResponse)
async def add_calendar(
    request: Request,
    session: Session = Depends(get_session),
    calendar_service: ICalendarService = Depends(get_calendar_service),
):
    """Manually trigger calendar synchronization."""

    # Run sync inline so the HTMX request only returns when sync completes.
    # This gives users visible feedback (loading indicator) matching
    # actual work. Run sync but suppress exceptions to avoid bubbling
    # errors to the admin UI
    with contextlib.suppress(Exception):
        await calendar_service.sync_calendars(session)

    return await get_calendars_partial(request, session, calendar_service)


# --- Partials: Gallery ---
@router.get("/partials/gallery", response_class=HTMLResponse)
async def get_gallery_partial(
    request: Request,
    preset_id: int | None = None,
    session: Session = Depends(get_session),
    media_service: IMediaService = Depends(get_media_service),
):
    data = await media_service.get_gallery_for_ui(session, preset_id)
    return templates.TemplateResponse(
        request,
        "partials/gallery.html",
        data,
    )


@router.post("/presets", response_class=HTMLResponse)
async def create_preset(
    request: Request,
    name: str = Form(...),
    session: Session = Depends(get_session),
    media_service: IMediaService = Depends(get_media_service),
):
    await media_service.create_preset(session, name)
    # Refresh gallery showing new preset
    return await get_gallery_partial(request, None, session, media_service)


@router.post("/upload", response_class=HTMLResponse)
async def upload_photos(
    request: Request,
    preset_id: int = Form(...),
    files: list[UploadFile] = File(...),
    session: Session = Depends(get_session),
    media_service: IMediaService = Depends(get_media_service),
):
    try:
        await media_service.upload_photos(session, preset_id, files)
    except ValueError as ve:
        # Build gallery context and show user-friendly error message
        data = await media_service.get_gallery_for_ui(session, preset_id)
        return templates.TemplateResponse(
            request,
            "partials/gallery.html",
            {**data, "error_message": str(ve)},
        )

    return await get_gallery_partial(request, preset_id, session, media_service)


@router.delete("/photos/{photo_id}", response_class=HTMLResponse)
async def delete_photo(
    request: Request,
    photo_id: int,
    session: Session = Depends(get_session),
    media_service: IMediaService = Depends(get_media_service),
):
    photo = await media_service.get_photo_by_id(session, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    preset_id = photo.preset_id
    await media_service.delete_photo_from_db(session, photo_id)

    return await get_gallery_partial(request, preset_id, session, media_service)


# --- Debug Panel ---
@router.get("/partials/debug", response_class=HTMLResponse)
async def get_debug_partial(request: Request):
    """Debug control panel for testing (HTMX partial)."""
    return templates.TemplateResponse(request, "partials/debug.html", {})


@router.post("/debug/simulate-alarm", response_class=HTMLResponse)
async def simulate_alarm(
    request: Request,
    delay_seconds: int = Form(...),
    session: Session = Depends(get_session),
    alarms_service: IAlarmsService = Depends(get_alarms_service),
):
    """Create a simulated alarm that appears after the specified delay."""
    await alarms_service.create_simulated_alarm(delay_seconds, session)

    return templates.TemplateResponse(
        request,
        "partials/debug.html",
        {
            "success_message": (
                f"Simulated alarm created! It will appear in {delay_seconds} seconds."
            )
        },
    )

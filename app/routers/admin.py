import logging
import os

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.modules.alarms.internal.infrastructure.presenter import render_debug_fragment
from app.modules.calendar.api.interfaces import ICalendarService, get_calendar_service
from app.modules.calendar.internal.infrastructure.presenter import render_calendars_fragment
from app.modules.media.api.interfaces import IMediaService, get_media_service
from app.modules.media.internal.infrastructure.presenter import render_gallery_fragment
from app.modules.settings.api.interfaces import ISettingsService, get_settings_service
from app.modules.settings.internal.infrastructure.presenter import render_settings_fragment
from app.modules.weather.api.interfaces import IWeatherService, get_weather_service
from app.template_config import templates

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
    presets = settings_service.list_presets()
    location_name = await weather_service.get_location_name(
        settings.weather_latitude,
        settings.weather_longitude,
    )
    return HTMLResponse(render_settings_fragment(settings, presets, location_name))


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
    presets = settings_service.list_presets()

    lat, lon, location_name = await weather_service.geocode_for_settings(location_query)
    if lat is not None and lon is not None:
        settings = settings_service.with_location_preview(settings, lat, lon)

    return HTMLResponse(render_settings_fragment(settings, presets, location_name))


@router.post("/settings", response_class=HTMLResponse)
async def update_settings(
    request: Request,  # noqa: ARG001
):
    raise HTTPException(
        status_code=410,
        detail="Deprecated admin mutation route. Use /api/v1/settings/* JSON endpoints.",
    )


# --- Partials: Calendars ---
@router.get("/partials/calendars", response_class=HTMLResponse)
async def get_calendars_partial(
    request: Request,  # noqa: ARG001
    calendar_service: ICalendarService = Depends(get_calendar_service),
):
    data = await calendar_service.get_calendars_for_ui()
    return HTMLResponse(render_calendars_fragment(data))


@router.post("/calendars", response_class=HTMLResponse)
async def add_calendar(
    request: Request,  # noqa: ARG001
):
    raise HTTPException(
        status_code=410,
        detail="Deprecated admin mutation route. Use /api/v1/calendar/* JSON endpoints.",
    )


# --- Partials: Gallery ---
@router.get("/partials/gallery", response_class=HTMLResponse)
async def get_gallery_partial(
    request: Request,  # noqa: ARG001
    preset_id: int | None = None,
    media_service: IMediaService = Depends(get_media_service),
):
    data = await media_service.get_gallery_for_ui(preset_id=preset_id)
    return HTMLResponse(render_gallery_fragment(data))


@router.post("/presets", response_class=HTMLResponse)
async def create_preset(
    request: Request,  # noqa: ARG001
):
    raise HTTPException(
        status_code=410,
        detail="Deprecated admin mutation route. Use POST /api/v1/presets.",
    )


@router.post("/upload", response_class=HTMLResponse)
async def upload_photos(
    request: Request,  # noqa: ARG001
):
    raise HTTPException(
        status_code=410,
        detail="Deprecated admin mutation route. Use POST /api/v1/presets/{preset_id}/images.",
    )


@router.delete("/photos/{photo_id}", response_class=HTMLResponse)
async def delete_photo(
    request: Request,  # noqa: ARG001
    photo_id: int,  # noqa: ARG001
):
    raise HTTPException(
        status_code=410,
        detail="Deprecated admin mutation route. Use DELETE /api/v1/images/{image_id}.",
    )


# --- Debug Panel ---
@router.get("/partials/debug", response_class=HTMLResponse)
async def get_debug_partial():
    """Debug control panel for testing (HTMX partial)."""
    return HTMLResponse(render_debug_fragment(success_message=None))


@router.post("/debug/simulate-alarm", response_class=HTMLResponse)
async def simulate_alarm(
    request: Request,  # noqa: ARG001
):
    raise HTTPException(
        status_code=410,
        detail="Deprecated admin mutation route. Use POST /api/v1/alarms/simulated.",
    )

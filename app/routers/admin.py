import contextlib
import logging
import os

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.db.models import (
    AlarmEvent,
    AppSettings,
    CalendarSource,
    CalendarSyncStatusEntry,
    Photo,
    Preset,
)
from app.db.session import get_session
from app.services.calendar_service import CalendarService
from app.services.image_service import GalleryManager
from app.services.weather_service import WeatherService
from app.utils.timezone import get_local_timezone_name

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)
gallery_manager = GalleryManager()


# --- Main Shell ---
@router.get("/")
async def admin_shell(request: Request):
    """Admin Shell with Sidebar"""
    debug_mode = os.getenv("WEBAPP_DEBUG", "").lower() in ("true", "1", "yes")
    return templates.TemplateResponse(request, "admin_base.html", {"debug_mode": debug_mode})


# --- Partials: Settings ---
@router.get("/partials/settings", response_class=HTMLResponse)
async def get_settings_partial(request: Request, session: Session = Depends(get_session)):
    settings = session.exec(select(AppSettings)).first()
    presets = session.exec(select(Preset)).all()

    location_name = ""
    if settings and settings.weather_latitude and settings.weather_longitude:
        try:
            # Simple reverse geocode for Admin UI context
            url = (
                f"https://nominatim.openstreetmap.org/reverse?"
                f"lat={settings.weather_latitude}&"
                f"lon={settings.weather_longitude}&format=json"
            )
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers={"User-Agent": "Espace-Image/1.0"})
                if resp.status_code == 200:
                    data = resp.json()
                    address = data.get("address", {})
                    city = (
                        address.get("city")
                        or address.get("town")
                        or address.get("village")
                        or "Unknown"
                    )
                    state = address.get("state") or address.get("region") or ""
                    location_name = f"{city}, {state}" if state else city
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
):
    """
    Geocodes the location query and returns the settings form
    pre-filled with the new coordinates (not saved yet).
    """
    settings = session.exec(select(AppSettings)).first()
    if not settings:
        settings = AppSettings()  # default

    presets = session.exec(select(Preset)).all()

    # Perform Geocoding
    result = await WeatherService.geocode_location(location_query)
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
    session: Session = Depends(get_session),
):
    # Basic validation for form inputs
    if latitude is not None and not (-90.0 <= latitude <= 90.0):
        raise HTTPException(status_code=422, detail="Latitude must be between -90 and 90")
    if longitude is not None and not (-180.0 <= longitude <= 180.0):
        raise HTTPException(status_code=422, detail="Longitude must be between -180 and 180")
    if duration is not None and duration <= 0:
        raise HTTPException(status_code=422, detail="Duration must be a positive integer")

    settings = session.exec(select(AppSettings)).first()
    if not settings:
        settings = AppSettings()

    # Validate active_preset_id if provided
    if active_preset_id is not None:
        preset = session.get(Preset, active_preset_id)
        if not preset:
            raise HTTPException(status_code=422, detail="Active preset not found")

    settings.active_preset_id = active_preset_id
    settings.weather_latitude = latitude
    settings.weather_longitude = longitude
    if duration is not None:
        settings.slideshow_duration = duration
    session.add(settings)
    session.commit()

    # Redirect to the main slideshow using HTMX
    response = HTMLResponse()
    response.headers["HX-Redirect"] = "/"
    return response


# --- Partials: Calendars ---
@router.get("/partials/calendars", response_class=HTMLResponse)
async def get_calendars_partial(request: Request, session: Session = Depends(get_session)):
    sources = session.exec(select(CalendarSource)).all()
    sync_statuses = {}
    for source in sources:
        if source.id:
            status = session.exec(
                select(CalendarSyncStatusEntry).where(
                    CalendarSyncStatusEntry.calendar_source_id == source.id
                )
            ).first()
            sync_statuses[source.id] = status
    return templates.TemplateResponse(
        request,
        "partials/calendars.html",
        {"sources": sources, "sync_statuses": sync_statuses},
    )


@router.post("/calendars", response_class=HTMLResponse)
async def add_calendar(
    request: Request,
    label: str = Form(...),
    url: str = Form(...),
    color: str = Form("#3182ce"),
    session: Session = Depends(get_session),
):
    source = CalendarSource(label=label, url=url, color=color)
    session.add(source)
    session.commit()
    return await get_calendars_partial(request, session)


@router.delete("/calendars/{source_id}", response_class=HTMLResponse)
async def delete_calendar(
    request: Request, source_id: int, session: Session = Depends(get_session)
):
    source = session.get(CalendarSource, source_id)
    if source:
        session.delete(source)
        session.commit()
    return await get_calendars_partial(request, session)


@router.post("/calendars/sync-now", response_class=HTMLResponse)
async def sync_calendars_now(
    request: Request,
    session: Session = Depends(get_session),
):
    """Manually trigger calendar synchronization."""

    # Run sync inline so the HTMX request only returns when sync completes.
    # This gives users visible feedback (loading indicator) matching
    # actual work. Run sync but suppress exceptions to avoid bubbling
    # errors to the admin UI
    with contextlib.suppress(Exception):
        await CalendarService.sync_calendar_events(session)

    return await get_calendars_partial(request, session)


# --- Partials: Gallery ---
@router.get("/partials/gallery", response_class=HTMLResponse)
async def get_gallery_partial(
    request: Request,
    preset_id: int | None = None,
    session: Session = Depends(get_session),
):
    presets = session.exec(select(Preset)).all()
    selected_preset = None
    photos = []

    if preset_id:
        selected_preset = session.get(Preset, preset_id)
        if selected_preset:
            photos = selected_preset.photos
    elif presets:
        # Default to first preset if available
        selected_preset = presets[0]
        photos = selected_preset.photos

    return templates.TemplateResponse(
        request,
        "partials/gallery.html",
        {
            "presets": presets,
            "selected_preset": selected_preset,
            "photos": photos,
        },
    )


@router.post("/presets", response_class=HTMLResponse)
async def create_preset(
    request: Request,
    name: str = Form(...),
    session: Session = Depends(get_session),
):
    preset = Preset(name=name)
    session.add(preset)
    session.commit()
    # Refresh gallery showing new preset
    return await get_gallery_partial(request, preset.id, session)


@router.post("/upload", response_class=HTMLResponse)
async def upload_photos(
    request: Request,
    preset_id: int = Form(...),
    files: list[UploadFile] = File(...),
    session: Session = Depends(get_session),
):
    preset = session.get(Preset, preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")

    for file in files:
        if not file.filename:
            continue
        try:
            content = await file.read()
            _path, stored_filename = gallery_manager.save_upload(
                content, file.filename, preset.name
            )
            photo = Photo(filename=stored_filename, preset_id=preset.id)
            session.add(photo)
        except ValueError as ve:
            # Build gallery context and show user-friendly error message
            presets = session.exec(select(Preset)).all()
            photos = preset.photos if preset else []
            return templates.TemplateResponse(
                request,
                "partials/gallery.html",
                {
                    "presets": presets,
                    "selected_preset": preset,
                    "photos": photos,
                    "error_message": str(ve),
                },
            )

    session.commit()
    return await get_gallery_partial(request, preset_id, session)


@router.delete("/photos/{photo_id}", response_class=HTMLResponse)
async def delete_photo(request: Request, photo_id: int, session: Session = Depends(get_session)):
    photo = session.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # Delete from disk
    preset_name = photo.preset.name if photo.preset else "Default"
    gallery_manager.delete_photo(photo.filename, preset_name)

    preset_id = photo.preset_id
    session.delete(photo)
    session.commit()

    return await get_gallery_partial(request, preset_id, session)


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
):
    """Create a simulated alarm that appears after the specified delay."""
    from datetime import datetime, timedelta
    from uuid import uuid4

    # Calculate trigger time (UTC-aware)
    from app.utils.timezone import ensure_utc_aware

    trigger_time = ensure_utc_aware(datetime.now() + timedelta(seconds=delay_seconds))

    # Create alarm event with unique UID
    alarm = AlarmEvent(
        uid=f"test-{uuid4()}",
        trigger_time=trigger_time,
    )

    session.add(alarm)
    session.commit()

    return templates.TemplateResponse(
        request,
        "partials/debug.html",
        {
            "success_message": (
                f"Simulated alarm created! It will appear in {delay_seconds} seconds."
            )
        },
    )


from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.db.models import AppSettings, CalendarSource, Photo, Preset
from app.db.session import get_session
from app.services.image_service import GalleryManager
from app.services.weather_service import WeatherService

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")
gallery_manager = GalleryManager()


# --- Main Shell ---
@router.get("/")
async def admin_shell(request: Request):
    """Admin Shell with Sidebar"""
    return templates.TemplateResponse(request, "admin_base.html", {})


# --- Partials: Settings ---
@router.get("/partials/settings", response_class=HTMLResponse)
async def get_settings_partial(
    request: Request, session: Session = Depends(get_session)
):
    settings = session.exec(select(AppSettings)).first()
    presets = session.exec(select(Preset)).all()

    location_name = ""
    if settings and settings.weather_latitude and settings.weather_longitude:
        try:
            # Simple reverse geocode for Admin UI context
            import httpx

            url = f"https://nominatim.openstreetmap.org/reverse?lat={settings.weather_latitude}&lon={settings.weather_longitude}&format=json"
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    url, headers={"User-Agent": "GeminiDashboard/1.0"}
                )
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
        except Exception as e:
            print(f"Geocoding error: {e}")

    return templates.TemplateResponse(
        request,
        "partials/settings.html",
        {"settings": settings, "presets": presets, "location_name": location_name},
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
        {"settings": settings, "presets": presets, "location_name": location_name},
    )


@router.post("/settings", response_class=HTMLResponse)
async def update_settings(
    request: Request,
    active_preset_id: int | None = Form(None),
    latitude: float = Form(...),
    longitude: float = Form(...),
    duration: int = Form(30),
    session: Session = Depends(get_session),
):
    settings = session.exec(select(AppSettings)).first()
    if not settings:
        settings = AppSettings()

    settings.active_preset_id = active_preset_id
    settings.weather_latitude = latitude
    settings.weather_longitude = longitude
    settings.slideshow_duration = duration
    session.add(settings)
    session.commit()

    # Return updated partial
    return await get_settings_partial(request, session)


# --- Partials: Calendars ---
@router.get("/partials/calendars", response_class=HTMLResponse)
async def get_calendars_partial(
    request: Request, session: Session = Depends(get_session)
):
    sources = session.exec(select(CalendarSource)).all()
    return templates.TemplateResponse(
        request, "partials/calendars.html", {"sources": sources}
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
        {"presets": presets, "selected_preset": selected_preset, "photos": photos},
    )


@router.post("/presets", response_class=HTMLResponse)
async def create_preset(
    request: Request, name: str = Form(...), session: Session = Depends(get_session)
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
        content = await file.read()
        gallery_manager.save_upload(content, file.filename, preset.name)
        photo = Photo(filename=file.filename, preset_id=preset.id)
        session.add(photo)

    session.commit()
    return await get_gallery_partial(request, preset_id, session)


@router.delete("/photos/{photo_id}", response_class=HTMLResponse)
async def delete_photo(
    request: Request, photo_id: int, session: Session = Depends(get_session)
):
    photo = session.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # We should delete from disk too (TODO: Add method to gallery_manager)
    # gallery_manager.delete_photo(photo.filename, photo.preset.name)

    preset_id = photo.preset_id
    session.delete(photo)
    session.commit()

    return await get_gallery_partial(request, preset_id, session)

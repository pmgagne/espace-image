from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.db.session import get_session
from app.db.models import AppSettings, Photo, Preset, AlarmEvent
from app.services.weather_service import WeatherService
from app.services.calendar_service import CalendarService
from datetime import datetime, timezone
import random

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/")
async def read_root(request: Request, session: Session = Depends(get_session)):
    """Modern Dashboard View"""
    return templates.TemplateResponse(request, "index.html", {"mode": "modern"})

@router.get("/legacy")
async def read_legacy(request: Request):
    """Legacy Dashboard View (iPad 2)"""
    return templates.TemplateResponse(request, "legacy/index.html", {"mode": "legacy"})

@router.get("/components/weather", response_class=HTMLResponse)
async def get_weather(session: Session = Depends(get_session)):
    """Returns HTML fragment for weather widget."""
    settings = session.exec(select(AppSettings)).first()
    if not settings:
        return "<div>No Settings</div>"
    
    weather = await WeatherService.get_current_weather(settings.weather_location, settings.weather_api_key)
    
    # We return a simple HTML string for HTMX to swap in
    return f"""
    <div class="weather-widget">
        <div class="temp">{weather['temp']}°C</div>
        <div class="condition">{weather['condition']}</div>
        <div class="location">{weather['location']}</div>
    </div>
    """

@router.get("/components/slide", response_class=HTMLResponse)
async def get_next_slide(mode: str = "modern", session: Session = Depends(get_session)):
    """Returns HTML fragment for the next slide."""
    settings = session.exec(select(AppSettings)).first()
    if not settings or not settings.active_preset_id:
        return "<div class='error'>No Preset Active</div>"
    
    # Get photos from active preset
    photos = session.exec(select(Photo).where(Photo.preset_id == settings.active_preset_id)).all()
    
    if not photos:
        return "<div class='error'>No Photos</div>"
    
    # Pick a random photo
    photo = random.choice(photos)
    
    # Determine image URL based on mode
    # For now, we assume we serve images directly from static or a specific endpoint
    # We need an endpoint to serve the actual image file.
    # Let's assume /images/{id}
    img_url = f"/images/{photo.id}?mode={mode}"
    
    return f"""
    <div class="slide fade-in">
        <img src="{img_url}" alt="Slide">
    </div>
    """

@router.get("/components/alarm", response_class=HTMLResponse)
async def check_alarm(session: Session = Depends(get_session)):
    """Checks for active alarms and returns modal HTML if one exists."""
    settings = session.exec(select(AppSettings)).first()
    if not settings or not settings.calendar_url:
        return ""
    
    # Fetch and parse calendar (In production, this should be a background task that updates the DB)
    # For this prototype, we'll do it on-demand but cached is better.
    # To keep it simple for now:
    # 1. Fetch ICS
    # 2. Check alarms
    
    # Check DB for active alarms first (optimization needed later)
    
    # TODO: Real implementation with background task
    # For now, return empty unless simulated
    return ""

@router.post("/api/alarms/{uid}/dismiss")
async def dismiss_alarm(uid: str, session: Session = Depends(get_session)):
    """Dismisses an alarm."""
    # Logic to mark alarm as dismissed in DB
    return {"status": "dismissed"}

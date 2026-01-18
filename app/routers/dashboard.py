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
    # Provide defaults if settings are missing to avoid empty displays
    location = settings.weather_location if settings else "Unknown"
    api_key = settings.weather_api_key if settings else None
    
    weather = await WeatherService.get_current_weather(location, api_key)
    
    return f"""
    <div id="weather-display" class="weather-info">
        <span class="temp">{weather['temp']}°C</span>
        <span class="condition">{weather['condition']}</span>
    </div>
    """

@router.get("/components/slide", response_class=HTMLResponse)
async def get_next_slide(mode: str = "modern", session: Session = Depends(get_session)):
    """Returns HTML fragment for the next slide."""
    settings = session.exec(select(AppSettings)).first()
    if not settings or not settings.active_preset_id:
        return "<div class='error-msg'>No Preset Active. Please configure in Admin.</div>"
    
    photos = session.exec(select(Photo).where(Photo.preset_id == settings.active_preset_id)).all()
    
    if not photos:
        return "<div class='error-msg'>No Photos found in the active preset.</div>"
    
    photo = random.choice(photos)
    img_url = f"/images/{photo.id}?mode={mode}"
    
    return f"""
    <div class="slide-container fade-in">
        <img src="{img_url}" class="full-slide" alt="Slide">
    </div>
    """

@router.get("/components/alarm", response_class=HTMLResponse)
async def check_alarm(mock: bool = False, session: Session = Depends(get_session)):
    """Checks for active alarms and returns modal HTML if one exists."""
    if mock:
        return """
        <div id="alarm-overlay" class="alarm-modal">
            <div class="alarm-content">
                <h1>⏰ ALARM</h1>
                <p>Mock Event: Time to wake up!</p>
                <button hx-post="/api/alarms/mock-1/dismiss" 
                        hx-target="#alarm-overlay" 
                        hx-swap="outerHTML"
                        class="dismiss-btn">Dismiss</button>
            </div>
        </div>
        """
    
    # Real logic placeholder
    return ""

@router.post("/api/alarms/{uid}/dismiss", response_class=HTMLResponse)
async def dismiss_alarm(uid: str, session: Session = Depends(get_session)):
    """Dismisses an alarm."""
    # Logic to mark alarm as dismissed in DB would go here.
    # For now, we return an empty string to remove the modal from the DOM via hx-swap.
    return ""

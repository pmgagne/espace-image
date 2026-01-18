from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.db.session import get_session
from app.db.models import AppSettings, Photo, AlarmEvent, CalendarSource
from app.services.weather_service import WeatherService
from app.services.calendar_service import CalendarService
from datetime import datetime
import random

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def read_root(request: Request, session: Session = Depends(get_session)):
    """Modern Dashboard View"""
    user_agent = request.headers.get("user-agent", "").lower()
    print(f"DEBUG: Incoming User-Agent: {user_agent}")  # Debugging log

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
    """Legacy Dashboard View (iPad 2)"""
    settings = session.exec(select(AppSettings)).first()
    return templates.TemplateResponse(
        request, "legacy/index.html", {"mode": "legacy", "settings": settings}
    )


@router.get("/components/weather", response_class=HTMLResponse)
async def get_weather(session: Session = Depends(get_session)):
    """Returns HTML fragment for weather widget."""
    settings = session.exec(select(AppSettings)).first()

    # Defaults if not set
    lat = settings.weather_latitude if settings else 45.5
    lon = settings.weather_longitude if settings else -73.5

    weather = await WeatherService.get_current_weather(lat, lon)

    return f"""
    <div id="weather-display" class="weather-info">
        <span class="temp">{weather["temp"]}°C</span>
        <span class="condition">{weather["condition"]}</span>
    </div>
    """


@router.get("/components/slide", response_class=HTMLResponse)
async def get_next_slide(mode: str = "modern", session: Session = Depends(get_session)):
    """Returns HTML fragment for the next slide."""
    settings = session.exec(select(AppSettings)).first()
    if not settings or not settings.active_preset_id:
        return (
            "<div class='error-msg'>No Preset Active. Please configure in Admin.</div>"
        )

    photos = session.exec(
        select(Photo).where(Photo.preset_id == settings.active_preset_id)
    ).all()

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

    # Real logic
    sources = session.exec(select(CalendarSource)).all()
    if not sources:
        return ""

    urls = [s.url for s in sources]
    alarms = await CalendarService.get_all_alarms(urls)

    if not alarms:
        return ""

    # Get the first alarm that isn't dismissed
    active_alarm = None
    for alarm in alarms:
        dismissed = session.exec(
            select(AlarmEvent).where(AlarmEvent.uid == alarm["uid"])
        ).first()
        if not dismissed:
            active_alarm = alarm
            break

    if not active_alarm:
        return ""

    return f"""
    <div id="alarm-overlay" class="alarm-modal">
        <div class="alarm-content">
            <h1>⏰ {active_alarm["name"]}</h1>
            <p>{active_alarm["description"] or "Event Started"}</p>
            <button hx-post="/api/alarms/{active_alarm["uid"]}/dismiss" 
                    hx-target="#alarm-overlay" 
                    hx-swap="outerHTML"
                    class="dismiss-btn">Dismiss</button>
        </div>
    </div>
    """


@router.post("/api/alarms/{uid}/dismiss", response_class=HTMLResponse)
async def dismiss_alarm(uid: str, session: Session = Depends(get_session)):
    """Dismisses an alarm."""
    # Check if already dismissed
    existing = session.exec(select(AlarmEvent).where(AlarmEvent.uid == uid)).first()
    if not existing:
        alarm_event = AlarmEvent(
            uid=uid, trigger_time=datetime.now(), dismissed_at=datetime.now()
        )
        session.add(alarm_event)
        session.commit()

    return ""

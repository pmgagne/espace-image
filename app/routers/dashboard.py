import random
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.db.models import AlarmEvent, AppSettings, CalendarSource, Photo
from app.db.session import get_session
from app.services.calendar_service import CalendarService
from app.services.weather_service import WeatherService

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
    """Checks for active alarms and returns a list of them if any exist."""
    
    active_alarms = []

    if mock:
        active_alarms = [
            {"uid": "mock-1", "name": "Meeting with Client", "description": "Discuss project roadmap", "time": "14:00"},
            {"uid": "mock-2", "name": "Dentist Appointment", "description": "Dr. Smith", "time": "16:30"}
        ]
    else:
        # Real logic
        sources = session.exec(select(CalendarSource)).all()
        if sources:
            urls = [s.url for s in sources]
            alarms = await CalendarService.get_all_alarms(urls)

            if alarms:
                # Filter out dismissed alarms
                for alarm in alarms:
                    dismissed = session.exec(
                        select(AlarmEvent).where(AlarmEvent.uid == alarm["uid"])
                    ).first()
                    if not dismissed:
                        active_alarms.append(alarm)

    if not active_alarms:
        return ""

    # Sort alarms by UID to ensure consistent HTML output for change detection
    active_alarms.sort(key=lambda x: x["uid"])

    # Generate HTML for all active alarms
    alarms_html = ""
    for alarm in active_alarms:
        alarms_html += f"""
        <div class="alarm-item">
            <div class="alarm-header">
                <span class="alarm-icon">📅</span>
                <span class="alarm-title">{alarm["name"]}</span>
            </div>
            <div class="alarm-body">
                {alarm.get("description") or "Event Started"}
            </div>
            <button hx-post="/api/alarms/{alarm["uid"]}/dismiss?mock={'true' if mock else 'false'}" 
                    hx-target="#alarm-poller" 
                    hx-swap="innerHTML"
                    class="dismiss-btn-small">Dismiss</button>
        </div>
        """

    return f"""
    <div id="alarm-box" class="alarm-box-container">
        {alarms_html}
    </div>
    """


@router.post("/api/alarms/{uid}/dismiss", response_class=HTMLResponse)
async def dismiss_alarm(uid: str, mock: bool = False, session: Session = Depends(get_session)):
    """Dismisses an alarm and returns the updated alarm list."""
    
    if not mock:
        # Check if already dismissed
        existing = session.exec(select(AlarmEvent).where(AlarmEvent.uid == uid)).first()
        if not existing:
            alarm_event = AlarmEvent(
                uid=uid, trigger_time=datetime.now(), dismissed_at=datetime.now()
            )
            session.add(alarm_event)
            session.commit()

    # Return the updated list immediately
    return await check_alarm(mock=mock, session=session)

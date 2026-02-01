import random
from datetime import UTC, datetime, timedelta

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
    """Modern Slideshow View"""
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
    """Legacy Slideshow View (iPad 2)"""
    settings = session.exec(select(AppSettings)).first()
    return templates.TemplateResponse(
        request, "legacy/index.html", {"mode": "legacy", "settings": settings}
    )


@router.get("/components/weather", response_class=HTMLResponse)
async def get_weather(session: Session = Depends(get_session)):
    """Returns HTML fragment for weather widget."""
    settings = session.exec(select(AppSettings)).first()

    if not settings or settings.weather_latitude is None or settings.weather_longitude is None:
        return """
        <div id="weather-display" class="weather-info">
            <span class="condition" style="font-size: 0.8em; opacity: 0.8;">No location defined</span>
        </div>
        """

    lat = settings.weather_latitude
    lon = settings.weather_longitude

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
async def check_alarm(
    mock: bool = False,
    tz_offset: int | None = None,
    session: Session = Depends(get_session),
):
    """Checks for active alarms and returns a list of them if any exist."""

    active_alarms = []

    now = datetime.now()
    purge_before = now - timedelta(days=30)
    dismissed_alarms = session.exec(
        select(AlarmEvent).where(
            (AlarmEvent.dismissed_at.is_not(None)) & (AlarmEvent.dismissed_at < purge_before)
        )
    ).all()
    for alarm_event in dismissed_alarms:
        session.delete(alarm_event)
    if dismissed_alarms:
        session.commit()

    if mock:
        active_alarms = [
            {
                "uid": "mock-1",
                "name": "Meeting with Client",
                "description": "Discuss project roadmap",
                "time": "14:00",
            },
            {
                "uid": "mock-2",
                "name": "Dentist Appointment",
                "description": "Dr. Smith",
                "time": "16:30",
            },
        ]
    else:
        # Real logic - fetch from calendar sources
        sources = session.exec(select(CalendarSource)).all()
        if sources:
            tz_offset_minutes = tz_offset if tz_offset is not None else 0
            utc_now = datetime.now(UTC)
            device_now = (utc_now - timedelta(minutes=tz_offset_minutes)).replace(tzinfo=None)
            device_midnight = device_now.replace(hour=0, minute=0, second=0, microsecond=0)
            device_midnight_utc = (device_midnight + timedelta(minutes=tz_offset_minutes)).replace(
                tzinfo=UTC
            )
            lookback_minutes = max(
                int((utc_now - device_midnight_utc).total_seconds() / 60),
                0,
            )
            import logging

            logger = logging.getLogger(__name__)
            logger.info(
                f"Alarm check: tz_offset={tz_offset_minutes}min, utc_now={utc_now}, "
                f"device_now={device_now}, lookback={lookback_minutes}min"
            )
            source_pairs = [
                (s.id if s.id is not None else index + 1, s.url) for index, s in enumerate(sources)
            ]
            alarms = await CalendarService.get_all_alarms(
                source_pairs,
                check_time=utc_now,
                lookback_minutes=lookback_minutes,
                tz_offset_minutes=tz_offset_minutes,
            )
            logger.info(f"Fetched {len(alarms)} alarms: {[(a['uid'], a['begin']) for a in alarms]}")

            if alarms:
                # Filter out dismissed alarms
                for alarm in alarms:
                    dismissed = session.exec(
                        select(AlarmEvent).where(AlarmEvent.uid == alarm["uid"])
                    ).first()
                    if not dismissed and ":" in alarm["uid"]:
                        raw_uid = alarm["uid"].split(":", 1)[1]
                        dismissed = session.exec(
                            select(AlarmEvent).where(AlarmEvent.uid == raw_uid)
                        ).first()
                    # Only include if alarm hasn't been dismissed
                    if not dismissed or dismissed.dismissed_at is None:
                        active_alarms.append(alarm)

        # Also fetch simulated alarms from database
        simulated_alarms = session.exec(
            select(AlarmEvent).where(
                (AlarmEvent.uid.like("test-%"))
                & (AlarmEvent.trigger_time <= now)
                & (AlarmEvent.dismissed_at.is_(None))
            )
        ).all()

        for alarm_event in simulated_alarms:
            active_alarms.append(
                {
                    "uid": alarm_event.uid,
                    "name": "Simulated Event",
                    "description": "Test alarm for debugging",
                    "time": alarm_event.trigger_time.strftime("%H:%M"),
                }
            )

    if not active_alarms:
        return ""

    # Sort alarms by UID to ensure consistent HTML output for change detection
    active_alarms.sort(key=lambda x: x["uid"])

    # Generate HTML for all active alarms
    alarms_html = ""
    tz_query = f"&tz_offset={tz_offset}" if tz_offset is not None else ""
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
            <button hx-post="/api/alarms/{alarm["uid"]}/dismiss?mock={"true" if mock else "false"}{tz_query}"
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
async def dismiss_alarm(
    uid: str,
    mock: bool = False,
    tz_offset: int | None = None,
    session: Session = Depends(get_session),
):
    """Dismisses an alarm and returns the updated alarm list."""

    if not mock:
        # Check if alarm already exists
        existing = session.exec(select(AlarmEvent).where(AlarmEvent.uid == uid)).first()
        if existing:
            # Update existing alarm record with dismissal time
            existing.dismissed_at = datetime.now()
            session.add(existing)
        else:
            # Create new alarm record (for alarms from calendar that haven't been seen yet)
            alarm_event = AlarmEvent(
                uid=uid, trigger_time=datetime.now(), dismissed_at=datetime.now()
            )
            session.add(alarm_event)
        session.commit()
        # Refresh session to ensure we get updated data
        session.expunge_all()

    # Return the updated list immediately
    return await check_alarm(mock=mock, tz_offset=tz_offset, session=session)

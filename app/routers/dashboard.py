import random
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.db.models import AlarmEvent, AppSettings, CalendarEventCache, Photo
from app.db.session import get_session
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


def _purge_old_dismissed_alarms(session: Session) -> None:
    """Delete dismissed alarms older than 30 days."""
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


async def _fetch_calendar_alarms(session: Session, _tz_offset: int | None = None) -> list[dict]:
    """Fetch alarms from cached calendar events and filter dismissed ones."""
    import logging

    logger = logging.getLogger(__name__)
    active_alarms = []

    # Query cached events within window (past 7 days to future 7 days)
    utc_now = datetime.now(UTC)
    window_start = utc_now - timedelta(days=7)
    window_end = utc_now + timedelta(days=7)

    cached_events = session.exec(
        select(CalendarEventCache).where(
            (CalendarEventCache.event_start >= window_start)
            & (CalendarEventCache.event_start <= window_end)
        )
    ).all()

    logger.info(f"Found {len(cached_events)} cached events in window")

    # Convert cached events to alarm format
    for event in cached_events:
        # Create composite UID: source_id:uid
        composite_uid = f"{event.calendar_source_id}:{event.uid}"

        # Check if dismissed
        dismissed = session.exec(select(AlarmEvent).where(AlarmEvent.uid == composite_uid)).first()

        # Fallback: also check raw uid without source_id prefix
        if not dismissed:
            dismissed = session.exec(select(AlarmEvent).where(AlarmEvent.uid == event.uid)).first()

        # Only include if not dismissed
        if not dismissed or dismissed.dismissed_at is None:
            # All-day event detection: if start is at 00:00 and end is at 23:59 or 00:00 next day
            is_all_day = False
            # End is either 23:59 same day or 00:00 next day
            if (
                event.event_start.hour == 0
                and event.event_start.minute == 0
                and (event.event_end - event.event_start).days >= 1
            ):
                is_all_day = True
            active_alarms.append(
                {
                    "uid": composite_uid,
                    "name": event.summary,
                    "start": event.event_start,
                    "end": event.event_end,
                    "all_day": is_all_day,
                }
            )

    return active_alarms


def _fetch_simulated_alarms(session: Session) -> list[dict]:
    """Fetch test/simulated alarms from database."""
    now = datetime.now()
    simulated_alarms = session.exec(
        select(AlarmEvent).where(
            (AlarmEvent.uid.like("test-%"))
            & (AlarmEvent.trigger_time <= now)
            & (AlarmEvent.dismissed_at.is_(None))
        )
    ).all()

    alarms = []
    for alarm_event in simulated_alarms:
        alarms.append(
            {
                "uid": alarm_event.uid,
                "name": "Simulated Event",
                "start": alarm_event.trigger_time,
                "end": alarm_event.trigger_time + timedelta(hours=1),
                "all_day": False,
            }
        )
    return alarms


def _render_alarms_html(
    active_alarms: list[dict], mock: bool = False, tz_offset: int | None = None
) -> str:
    """Generate HTML for alarm list."""
    if not active_alarms:
        return ""

    # Sort alarms by UID to ensure consistent HTML output for change detection
    active_alarms.sort(key=lambda x: x["uid"])

    tz_query = f"&tz_offset={tz_offset}" if tz_offset is not None else ""
    alarms_html = ""
    for alarm in active_alarms:
        # Provide ISO strings for start/end, and all_day flag
        start_iso = ""
        end_iso = ""
        all_day = False
        try:
            if "start" in alarm and hasattr(alarm["start"], "isoformat"):
                start_iso = alarm["start"].isoformat()
            if "end" in alarm and hasattr(alarm["end"], "isoformat"):
                end_iso = alarm["end"].isoformat()
            if "all_day" in alarm:
                all_day = alarm["all_day"]
        except Exception:
            pass

        alarms_html += f"""
        <div class="alarm-item">
            <div class="alarm-header">
                <span class="alarm-icon">📅</span>
                <span class="alarm-title">{alarm["name"]}</span>
            </div>
            <div class="alarm-body">
                <span class="alarm-time alarm-time-small" data-start="{start_iso}" data-end="{end_iso}" data-allday="{str(all_day).lower()}"></span>
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


@router.get("/components/alarm", response_class=HTMLResponse)
async def check_alarm(
    mock: bool = False,
    tz_offset: int | None = None,
    session: Session = Depends(get_session),
):
    """Checks for active alarms and returns a list of them if any exist."""
    _purge_old_dismissed_alarms(session)

    if mock:
        # Provide ISO datetimes so client-side can format using browser locale
        now = datetime.now()
        dt1 = now.replace(hour=14, minute=0, second=0, microsecond=0)
        dt2 = now.replace(hour=16, minute=30, second=0, microsecond=0)
        active_alarms = [
            {
                "uid": "mock-1",
                "name": "Meeting with Client",
                "start": dt1,
                "end": dt1 + timedelta(hours=1),
                "all_day": False,
            },
            {
                "uid": "mock-2",
                "name": "Dentist Appointment",
                "start": dt2,
                "end": dt2 + timedelta(hours=1),
                "all_day": False,
            },
            {
                "uid": "mock-3",
                "name": "Journée pédagogique",
                "start": now.replace(hour=0, minute=0, second=0, microsecond=0),
                "end": (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
                "all_day": True,
            },
        ]
    else:
        # Fetch real alarms from calendars and simulated alarms
        calendar_alarms = await _fetch_calendar_alarms(session, tz_offset)
        simulated_alarms = _fetch_simulated_alarms(session)
        active_alarms = calendar_alarms + simulated_alarms

    return _render_alarms_html(active_alarms, mock, tz_offset)


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

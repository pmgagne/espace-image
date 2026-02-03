import random
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.db.models import (
    AlarmEvent,
    AppSettings,
    CalendarEventCache,
    CalendarSource,
    CalendarSyncStatusEntry,
    Photo,
)
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

    # Select events that overlap the window (start <= window_end AND end >= window_start)
    cached_events = session.exec(
        select(CalendarEventCache).where(
            (CalendarEventCache.event_start <= window_end)
            & (CalendarEventCache.event_end >= window_start)
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

    from datetime import datetime as _datetime

    active_alarms.sort(key=lambda x: x.get("start") or _datetime.min, reverse=True)

    tz_query = f"&tz_offset={tz_offset}" if tz_offset is not None else ""
    alarms_html = ""
    for alarm in active_alarms:
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

        fallback_text = _format_fallback_datetime(
            alarm.get("start"), alarm.get("end"), all_day, start_iso
        )

        alarms_html += _render_alarm_item(
            alarm, fallback_text, start_iso, end_iso, all_day, mock, tz_query
        )

    return f"""
    <div id="alarm-box" class="alarm-box-container">
        {alarms_html}
    </div>
    """


def _format_fallback_datetime(dt_obj, end_obj, all_day_flag: bool, start_iso_str: str) -> str:
    """Format a human-readable fallback string for an alarm datetime (French)."""
    try:
        if not dt_obj:
            return ""
        now_local = datetime.now(UTC)
        today = datetime(now_local.year, now_local.month, now_local.day, tzinfo=UTC)
        start_dt = dt_obj if dt_obj.tzinfo is not None else dt_obj.replace(tzinfo=UTC)
        start_day = datetime(start_dt.year, start_dt.month, start_dt.day, tzinfo=UTC)
        diff_days = (start_day - today).days

        if diff_days == 0:
            day_text = "Aujourd'hui"
        elif diff_days == 1:
            day_text = "Demain"
        else:
            days = [
                "Dimanche",
                "Lundi",
                "Mardi",
                "Mercredi",
                "Jeudi",
                "Vendredi",
                "Samedi",
            ]
            idx = start_dt.weekday() + 1 if start_dt.weekday() < 6 else 0
            month_names = [
                "janvier",
                "février",
                "mars",
                "avril",
                "mai",
                "juin",
                "juillet",
                "août",
                "septembre",
                "octobre",
                "novembre",
                "décembre",
            ]
            month = month_names[start_dt.month - 1]
            day_num = start_dt.day
            year_part = "" if start_dt.year == now_local.year else f" {start_dt.year}"
            day_text = f"{days[idx]}, {day_num} {month}{year_part}"

        if all_day_flag:
            return day_text

        def pad(n: int) -> str:
            return str(n).zfill(2)

        t1 = f"{pad(start_dt.hour)}:{pad(start_dt.minute)}"
        if end_obj:
            end_dt = end_obj if end_obj.tzinfo is not None else end_obj.replace(tzinfo=UTC)
            t2 = f"{pad(end_dt.hour)}:{pad(end_dt.minute)}"
            time_text = f"{t1}-{t2}" if t1 != t2 else t1
        else:
            time_text = t1

        return f"{day_text} {time_text}"
    except Exception:
        return start_iso_str or ""


def _render_alarm_item(
    alarm: dict,
    fallback_text: str,
    start_iso: str,
    end_iso: str,
    all_day: bool,
    mock: bool,
    tz_query: str,
) -> str:
    """Render a single alarm item HTML snippet."""
    uid = alarm.get("uid")
    name = alarm.get("name", "")
    return f"""
        <div class="alarm-item">
            <div class="alarm-header">
                <span class="alarm-icon">📅</span>
                <span class="alarm-title">{name}</span>
            </div>
            <div class="alarm-body">
                <span class="alarm-time alarm-time-small" data-start="{start_iso}" data-end="{end_iso}" data-allday="{str(all_day).lower()}">{fallback_text}</span>
            </div>
            <button hx-post="/api/alarms/{uid}/dismiss?mock={"true" if mock else "false"}{tz_query}"
                    hx-target="#alarm-poller"
                    hx-swap="innerHTML"
                    class="dismiss-btn-small">Dismiss</button>
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


@router.get("/debug/calendar-events", response_class=JSONResponse)
async def debug_calendar_events(session: Session = Depends(get_session)) -> JSONResponse:
    """Return cached calendar events and dismissed alarms for debugging."""
    cached = session.exec(select(CalendarEventCache)).all()
    alarms = session.exec(select(AlarmEvent)).all()

    events_out = [
        {
            "calendar_source_id": ev.calendar_source_id,
            "uid": ev.uid,
            "start": ev.event_start.isoformat(),
            "end": ev.event_end.isoformat(),
            "summary": ev.summary,
        }
        for ev in cached
    ]

    alarms_out = [
        {
            "uid": a.uid,
            "trigger_time": a.trigger_time.isoformat(),
            "dismissed_at": a.dismissed_at.isoformat() if a.dismissed_at else None,
        }
        for a in alarms
    ]

    return JSONResponse({"cached_events": events_out, "alarm_events": alarms_out})


@router.get("/debug/calendars", response_class=JSONResponse)
async def debug_calendars(session: Session = Depends(get_session)) -> JSONResponse:
    """Return configured calendar sources and their sync status for debugging."""
    sources = session.exec(select(CalendarSource)).all()
    statuses = session.exec(select(CalendarSyncStatusEntry)).all()

    src_out = [{"id": s.id, "label": s.label, "url": s.url} for s in sources]

    status_out = [
        {
            "calendar_source_id": st.calendar_source_id,
            "last_synced_at": st.last_synced_at.isoformat() if st.last_synced_at else None,
            "next_sync_at": st.next_sync_at.isoformat() if st.next_sync_at else None,
            "sync_status": st.sync_status,
            "error_message": st.error_message,
            "error_count": st.error_count,
        }
        for st in statuses
    ]

    return JSONResponse({"sources": src_out, "statuses": status_out})


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
            # Try to find a matching cached calendar event to preserve the event's start time
            trigger_time = datetime.now()
            try:
                # CalendarEventCache stores events with calendar_source_id + uid as composite in the UI
                # Try both composite and raw uid lookups
                cached = session.exec(
                    select(CalendarEventCache).where(CalendarEventCache.uid == uid)
                ).first()
                if not cached and uid and ":" in uid:
                    # Try to split composite UID and lookup by raw uid
                    _src, raw_uid = uid.split(":", 1)
                    cached = session.exec(
                        select(CalendarEventCache).where(CalendarEventCache.uid == raw_uid)
                    ).first()

                if cached:
                    trigger_time = cached.event_start
            except Exception:
                # Fall back to now on any DB lookup error
                trigger_time = datetime.now()

            alarm_event = AlarmEvent(
                uid=uid, trigger_time=trigger_time, dismissed_at=datetime.now()
            )
            session.add(alarm_event)
        session.commit()
        # Refresh session to ensure we get updated data
        session.expunge_all()

    # Return the updated list immediately
    return await check_alarm(mock=mock, tz_offset=tz_offset, session=session)

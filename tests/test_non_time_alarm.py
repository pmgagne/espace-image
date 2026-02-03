from datetime import UTC, datetime, timedelta

from app.routers import dashboard
from app.services.calendar_service import CalendarService


def _build_ics_with_proximity(start: datetime, end: datetime) -> str:
    return f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Espace-Image//EN
BEGIN:VEVENT
UID:prox-event@example.com
DTSTAMP:{start.strftime("%Y%m%dT%H%M%SZ")}
DTSTART:{start.strftime("%Y%m%dT%H%M%SZ")}
DTEND:{end.strftime("%Y%m%dT%H%M%SZ")}
SUMMARY:Proximity Event
BEGIN:VALARM
ACTION:PROXIMITY
PROXIMITY:DEPART
END:VALARM
END:VEVENT
END:VCALENDAR"""


def test_extract_events_detects_proximity():
    now = datetime(2026, 2, 3, 10, 0, 0, tzinfo=UTC)
    start = now + timedelta(minutes=10)
    end = start + timedelta(hours=1)

    ics = _build_ics_with_proximity(start, end)

    events = CalendarService.extract_events_from_ics(
        ics, source_id=1, window_start=now - timedelta(days=1), window_end=now + timedelta(days=1)
    )

    assert len(events) == 1
    ev = events[0]
    assert ev.get("uid") == "prox-event@example.com"
    assert ev.get("has_non_time_alarm") is True


def test_render_alarms_sorted_newest_first():
    # Create two alarms with different start times
    now = datetime.now(UTC)
    a1 = {
        "uid": "a1",
        "name": "Older",
        "start": now - timedelta(hours=2),
        "end": now - timedelta(hours=1),
        "all_day": False,
    }
    a2 = {
        "uid": "a2",
        "name": "Newer",
        "start": now - timedelta(minutes=10),
        "end": now + timedelta(hours=1),
        "all_day": False,
    }

    # Provide in older-first order
    html = dashboard._render_alarms_html([a1, a2], mock=False, tz_offset=None)

    # Newer should appear before Older in the produced HTML
    idx_newer = html.find("Newer")
    idx_older = html.find("Older")
    assert idx_newer != -1 and idx_older != -1
    assert idx_newer < idx_older

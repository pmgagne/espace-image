from datetime import UTC, datetime

from app.services.calendar_service import CalendarService


def test_recurring_event_expansion():
    # Daily event for 3 occurrences
    ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Espace-Image//EN
BEGIN:VEVENT
UID:recurring1@example.com
DTSTAMP:20260101T000000Z
DTSTART:20260101T100000Z
DTEND:20260101T110000Z
RRULE:FREQ=DAILY;COUNT=3
SUMMARY:Daily Standup
END:VEVENT
END:VCALENDAR"""

    window_start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    window_end = datetime(2026, 1, 5, 0, 0, 0, tzinfo=UTC)

    events = CalendarService.extract_events_from_ics(
        ics, source_id=1, window_start=window_start, window_end=window_end
    )

    assert len(events) == 3
    starts = sorted(ev["event_start"] for ev in events)
    assert starts[0] == datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    assert starts[1] == datetime(2026, 1, 2, 10, 0, 0, tzinfo=UTC)
    assert starts[2] == datetime(2026, 1, 3, 10, 0, 0, tzinfo=UTC)

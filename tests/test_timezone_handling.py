from datetime import UTC, datetime

from app.services.calendar_service import CalendarService


def test_naive_event_gets_local_tz(monkeypatch):
    # Use Montreal timezone for this test
    monkeypatch.setenv("TZ", "America/Montreal")

    ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//test//
BEGIN:VEVENT
UID:uid1@example.com
DTSTAMP:20260201T120000Z
DTSTART:20260210T230000
DTEND:20260210T233000
SUMMARY:Naive event
END:VEVENT
END:VCALENDAR
"""

    window_start = datetime(2026, 2, 9, tzinfo=UTC)
    window_end = datetime(2026, 2, 12, tzinfo=UTC)

    events = CalendarService.extract_events_from_ics(
        ics, source_id=1, window_start=window_start, window_end=window_end
    )

    assert len(events) == 1
    ev = events[0]
    assert ev["event_start"] is not None
    # The local wall time should still be 23:00 (we attach local tz, not convert)
    assert ev["event_start"].hour == 23
    # tzinfo should be present after parsing and fallback
    assert ev["event_start"].tzinfo is not None

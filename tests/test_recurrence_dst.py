from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.services.calendar_service import CalendarService


def test_biweekly_all_day_event_tzid_preserved():
    ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//test//
BEGIN:VEVENT
UID:biweekly@example.com
DTSTAMP:20260101T000000Z
DTSTART;VALUE=DATE:20260116
DTEND;VALUE=DATE:20260117
RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=FR
TZID:America/Toronto
SUMMARY:Biweekly Friday Off
END:VEVENT
END:VCALENDAR
"""

    window_start = datetime(2026, 1, 15, tzinfo=UTC)
    window_end = datetime(2026, 1, 31, tzinfo=UTC)

    events = CalendarService.extract_events_from_ics(
        ics, source_id=1, window_start=window_start, window_end=window_end
    )

    # Expect two occurrences in the window: 2026-01-16 and 2026-01-30
    assert len(events) >= 2
    starts = sorted([e["event_start"].date() for e in events if e.get("event_start")])
    assert datetime(2026, 1, 16).date() in starts
    assert datetime(2026, 1, 30).date() in starts

    # TZID should be captured on each event dict
    for ev in events:
        assert "tzid" in ev
        if ev["event_start"] is not None:
            assert ev["event_start"].tzinfo is not None


def test_weekly_across_dst_preserves_wall_time():
    # Weekly event at 09:00 America/Toronto around DST transition (DST 2026-03-08)
    ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//test//
BEGIN:VEVENT
UID:dst-weekly@example.com
DTSTAMP:20260301T000000Z
DTSTART;TZID=America/Toronto:20260307T090000
RRULE:FREQ=WEEKLY;COUNT=3
SUMMARY:Weekly morning
END:VEVENT
END:VCALENDAR
"""

    window_start = datetime(2026, 3, 6, tzinfo=UTC)
    window_end = datetime(2026, 3, 16, tzinfo=UTC)

    events = CalendarService.extract_events_from_ics(
        ics, source_id=2, window_start=window_start, window_end=window_end
    )

    # Expect occurrences on 2026-03-07 and 2026-03-14 (both should be 09:00 local wall time)
    dates = {
        e["event_start"].astimezone(e["event_start"].tzinfo).date(): e
        for e in events
        if e.get("event_start")
    }
    assert datetime(2026, 3, 7).date() in dates
    assert datetime(2026, 3, 14).date() in dates

    ev1 = dates[datetime(2026, 3, 7).date()]
    ev2 = dates[datetime(2026, 3, 14).date()]

    # Convert to the original TZ and assert wall-clock hour is 09:00
    assert ev1["tzid"] is not None
    assert ev2["tzid"] is not None
    tz1 = ZoneInfo(ev1["tzid"])
    tz2 = ZoneInfo(ev2["tzid"])
    assert ev1["event_start"].astimezone(tz1).hour == 9
    assert ev2["event_start"].astimezone(tz2).hour == 9

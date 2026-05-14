"""Tests for calendar element alarm normalization pipeline."""

import asyncio

from sqlmodel import select

from app.db.models import AlarmEvent, CalendarElement, CalendarSource
from app.modules.calendar.internal.infrastructure.alarm_normalizer import (
    CalendarAlarmNormalizer,
)


def test_normalize_alarm_occurrences_from_calendar_elements(session) -> None:
    """Recurring items in calendar_elements should produce alarm occurrences."""
    source = CalendarSource(label="Test", url="https://caldav.icloud.com/test")
    session.add(source)
    session.commit()
    session.refresh(source)

    raw_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//tests//EN
BEGIN:VEVENT
UID:recurring-1
DTSTART:20260101T100000Z
DTEND:20260101T110000Z
RRULE:FREQ=DAILY;COUNT=2
SUMMARY:Recurring test
BEGIN:VALARM
ACTION:DISPLAY
TRIGGER:-PT15M
DESCRIPTION:Reminder
END:VALARM
END:VEVENT
END:VCALENDAR
"""

    session.add(
        CalendarElement(
            calendar_source_id=source.id,
            uid="recurring-1.ics",
            href="https://caldav.icloud.com/test/recurring-1.ics",
            etag="etag-1",
            raw_ics=raw_ics,
        )
    )
    session.commit()

    inserted = asyncio.run(CalendarAlarmNormalizer.normalize(session))

    alarms = list(
        session.exec(select(AlarmEvent).where(AlarmEvent.calendar_source_id == source.id)).all()
    )

    assert inserted == 2
    assert len(alarms) == 2
    assert all(alarm.calendar_event_uid for alarm in alarms)
    assert all(alarm.trigger_time is not None for alarm in alarms)

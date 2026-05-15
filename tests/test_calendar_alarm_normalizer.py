"""Tests for calendar element alarm normalization pipeline."""

import asyncio
from datetime import UTC, date, datetime
from unittest.mock import patch

from sqlmodel import select

from app.db.models import AlarmEntryType, AlarmEvent, CalendarElement, CalendarSource
from app.modules.calendar.internal.infrastructure.alarm_normalizer import (
    CalendarAlarmNormalizer,
)


def test_normalize_alarm_occurrences_from_calendar_elements(session) -> None:
    """Recurring items in calendar_elements should produce event and alarm rows."""
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

    inserted = asyncio.run(
        CalendarAlarmNormalizer.normalize(
            session,
            start_date=date(2026, 1, 1),
            days=3,
        )
    )

    alarms = list(
        session.exec(select(AlarmEvent).where(AlarmEvent.calendar_source_id == source.id)).all()
    )

    assert inserted == 4
    assert len(alarms) == 4
    assert all(alarm.calendar_event_uid for alarm in alarms)
    assert all(alarm.trigger_time is not None for alarm in alarms)
    event_rows = [alarm for alarm in alarms if alarm.entry_type == AlarmEntryType.EVENT]
    alarm_rows = [alarm for alarm in alarms if alarm.entry_type == AlarmEntryType.ALARM]
    assert len(event_rows) == 2
    assert len(alarm_rows) == 2


def test_normalize_alarm_occurrences_with_multiple_valarms(session) -> None:
    """One occurrence with two VALARMs should create one event row and two alarm rows."""
    source = CalendarSource(label="Test", url="https://caldav.icloud.com/test")
    session.add(source)
    session.commit()
    session.refresh(source)

    raw_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//tests//EN
BEGIN:VEVENT
UID:with-two-alarms
DTSTART:20260101T100000Z
DTEND:20260101T110000Z
SUMMARY:Two alarm test
BEGIN:VALARM
ACTION:DISPLAY
TRIGGER:-PT30M
DESCRIPTION:Reminder 1
END:VALARM
BEGIN:VALARM
ACTION:DISPLAY
TRIGGER:-PT5M
DESCRIPTION:Reminder 2
END:VALARM
END:VEVENT
END:VCALENDAR
"""

    session.add(
        CalendarElement(
            calendar_source_id=source.id,
            uid="with-two-alarms.ics",
            href="https://caldav.icloud.com/test/with-two-alarms.ics",
            etag="etag-1",
            raw_ics=raw_ics,
        )
    )
    session.commit()

    inserted = asyncio.run(
        CalendarAlarmNormalizer.normalize(
            session,
            start_date=date(2026, 1, 1),
            days=1,
        )
    )

    alarms = list(
        session.exec(select(AlarmEvent).where(AlarmEvent.calendar_source_id == source.id)).all()
    )
    event_rows = [alarm for alarm in alarms if alarm.entry_type == AlarmEntryType.EVENT]
    alarm_rows = [alarm for alarm in alarms if alarm.entry_type == AlarmEntryType.ALARM]

    assert inserted == 3
    assert len(alarms) == 3
    assert len(event_rows) == 1
    assert len(alarm_rows) == 2


def test_default_window_bounds_include_previous_utc_day() -> None:
    """Default normalization window should include the prior UTC day for local-evening events."""
    mocked_now = datetime(2026, 5, 15, 1, 30, tzinfo=UTC)

    with patch(
        "app.modules.calendar.internal.infrastructure.alarm_normalizer.datetime"
    ) as mocked_datetime:
        mocked_datetime.now.return_value = mocked_now
        mocked_datetime.side_effect = datetime

        start, end = CalendarAlarmNormalizer._window_bounds(start_date=None, days=30)

    assert start == datetime(2026, 5, 14, 0, 0, tzinfo=UTC)
    assert end == datetime(2026, 6, 13, 0, 0, tzinfo=UTC)

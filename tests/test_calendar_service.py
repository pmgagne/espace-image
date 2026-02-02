import asyncio
from datetime import UTC, datetime, timedelta

from sqlmodel import select

from app.db.models import (
    CalendarEventCache,
    CalendarSource,
    CalendarSyncStatus,
    CalendarSyncStatusEntry,
)
from app.services.calendar_service import CalendarService

# Sample ICS content
SAMPLE_ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//hacksw/handcal//NONSGML v1.0//EN
BEGIN:VEVENT
UID:event1@example.com
DTSTAMP:20230101T000000Z
DTSTART:20260116T100000Z
DTEND:20260116T110000Z
SUMMARY:Meeting in 10 mins
END:VEVENT
BEGIN:VEVENT
UID:event2@example.com
DTSTAMP:20230101T000000Z
DTSTART:20260116T120000Z
DTEND:20260116T130000Z
SUMMARY:Lunch later
END:VEVENT
END:VCALENDAR"""


def test_parse_ics():
    calendar = CalendarService.parse_ics(SAMPLE_ICS)
    assert len(calendar.events) == 2


def test_get_upcoming_alarms():
    calendar = CalendarService.parse_ics(SAMPLE_ICS)

    # Mock "now" as 2026-01-16 09:50:00 UTC (10 mins before event1)
    # Note: ICS library uses Arrow objects or strict datetime.
    # The SAMPLE_ICS has Z (UTC) times.

    now = datetime(2026, 1, 16, 9, 50, 0, tzinfo=UTC)

    alarms = CalendarService.get_upcoming_alarms(calendar, now, lookahead_minutes=15)

    assert len(alarms) == 1
    assert alarms[0]["uid"] == "event1@example.com"
    assert alarms[0]["name"] == "Meeting in 10 mins"


def test_no_upcoming_alarms():
    calendar = CalendarService.parse_ics(SAMPLE_ICS)

    # Mock "now" as 2026-01-16 09:00:00 UTC (1 hour before event1)
    now = datetime(2026, 1, 16, 9, 0, 0, tzinfo=UTC)

    alarms = CalendarService.get_upcoming_alarms(calendar, now, lookahead_minutes=15)

    assert len(alarms) == 0


def _build_ics(start: datetime, end: datetime) -> str:
    return f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Espace-Image//EN
BEGIN:VEVENT
UID:event-dynamic@example.com
DTSTAMP:{start.strftime("%Y%m%dT%H%M%SZ")}
DTSTART:{start.strftime("%Y%m%dT%H%M%SZ")}
DTEND:{end.strftime("%Y%m%dT%H%M%SZ")}
SUMMARY:Dynamic Event
DESCRIPTION:Test event
END:VEVENT
END:VCALENDAR"""


def test_sync_calendar_events_success(session):
    now = datetime.now(UTC)
    start = now + timedelta(hours=1)
    end = now + timedelta(hours=2)
    ics_content = _build_ics(start, end)

    source = CalendarSource(label="Test", url="webcal://example.com/test.ics")
    session.add(source)
    session.commit()
    session.refresh(source)

    async def _fake_fetch(url: str) -> str | None:
        return ics_content

    original_fetch = CalendarService.fetch_ics
    CalendarService.fetch_ics = _fake_fetch
    try:
        asyncio.run(CalendarService.sync_calendar_events(session))
    finally:
        CalendarService.fetch_ics = original_fetch

    cached = session.exec(
        select(CalendarEventCache).where(CalendarEventCache.calendar_source_id == source.id)
    ).all()

    assert len(cached) == 1

    status = session.exec(
        select(CalendarSyncStatusEntry).where(
            CalendarSyncStatusEntry.calendar_source_id == source.id
        )
    ).first()

    assert status is not None
    assert status.sync_status == CalendarSyncStatus.SUCCESS


def test_sync_calendar_events_failure(session):
    source = CalendarSource(label="Test", url="webcal://example.com/test.ics")
    session.add(source)
    session.commit()
    session.refresh(source)

    async def _fake_fetch(url: str) -> str | None:
        return None

    original_fetch = CalendarService.fetch_ics
    CalendarService.fetch_ics = _fake_fetch
    try:
        asyncio.run(CalendarService.sync_calendar_events(session))
    finally:
        CalendarService.fetch_ics = original_fetch

    status = session.exec(
        select(CalendarSyncStatusEntry).where(
            CalendarSyncStatusEntry.calendar_source_id == source.id
        )
    ).first()

    assert status is not None
    assert status.sync_status == CalendarSyncStatus.FAILED
    assert status.error_count >= 1

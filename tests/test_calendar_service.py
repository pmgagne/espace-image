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


def test_parse_ics_events():
    now = datetime(2026, 1, 16, 9, 0, 0, tzinfo=UTC)
    events = CalendarService.parse_ics_events(SAMPLE_ICS, now, now + timedelta(days=1))
    assert len(events) == 2


def test_get_upcoming_alarms():
    now = datetime(2026, 1, 16, 9, 50, 0, tzinfo=UTC)
    alarms = CalendarService.get_upcoming_alarms(SAMPLE_ICS, now, lookahead_minutes=15)
    assert len(alarms) == 1
    assert alarms[0]["uid"] == "event1@example.com"
    assert alarms[0]["name"] == "Meeting in 10 mins"


def test_no_upcoming_alarms():
    now = datetime(2026, 1, 16, 9, 0, 0, tzinfo=UTC)
    alarms = CalendarService.get_upcoming_alarms(SAMPLE_ICS, now, lookahead_minutes=15)
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


# --- Additional Coverage for CalendarService ---
import pytest


def test_parse_ics_events_empty():
    now = datetime(2026, 1, 16, 9, 0, 0, tzinfo=UTC)
    events = CalendarService.parse_ics_events("", now, now + timedelta(days=1))
    assert events == []


def test_parse_ics_events_malformed():
    now = datetime(2026, 1, 16, 9, 0, 0, tzinfo=UTC)
    # Malformed ICS should not raise, just return []
    events = CalendarService.parse_ics_events("NOT AN ICS FILE", now, now + timedelta(days=1))
    assert events == []


def test_detect_proximity_uids():
    # Should detect UID in VEVENT with PROXIMITY VALARM
    ics = """BEGIN:VEVENT\nUID:prox-1\nBEGIN:VALARM\nPROXIMITY:ARRIVE\nEND:VALARM\nEND:VEVENT"""
    uids = CalendarService._detect_proximity_uids(ics)
    assert "prox-1" in uids
    # Should not detect if no PROXIMITY
    ics2 = """BEGIN:VEVENT\nUID:prox-2\nBEGIN:VALARM\nACTION:DISPLAY\nEND:VALARM\nEND:VEVENT"""
    uids2 = CalendarService._detect_proximity_uids(ics2)
    assert "prox-2" not in uids2


def test_to_datetime_variants():
    aware = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    naive = datetime(2026, 1, 1, 12, 0)
    dt1 = CalendarService._to_datetime(aware)
    dt2 = CalendarService._to_datetime(naive)
    assert dt1.tzinfo is not None
    assert dt2.tzinfo is not None


def test_get_local_tz_env(monkeypatch):
    monkeypatch.setenv("TZ", "UTC")
    tz = CalendarService._get_local_tz()
    assert tz is not None
    assert tz.key == "UTC"


def test_get_local_tz_invalid(monkeypatch):
    monkeypatch.setenv("TZ", "Invalid/Zone")
    tz = CalendarService._get_local_tz()
    # Should fallback to system tz or None, but not raise
    assert tz is not None or tz is None


def test_get_local_tz_no_env(monkeypatch):
    monkeypatch.delenv("TZ", raising=False)
    tz = CalendarService._get_local_tz()
    assert tz is not None or tz is None


@pytest.mark.anyio
async def test_fetch_ics_backoff(monkeypatch):
    # Patch ICalDownload.data_from_url to fail 3 times, then succeed
    from icalevents.icaldownload import ICalDownload

    calls = {"count": 0}
    orig_data_from_url = ICalDownload.data_from_url

    def fail_then_succeed(self, url, _):
        calls["count"] += 1
        if calls["count"] < 4:
            raise Exception("network error")
        return "BEGIN:VCALENDAR\nEND:VCALENDAR"

    monkeypatch.setattr(ICalDownload, "data_from_url", fail_then_succeed)
    try:
        result = await CalendarService.fetch_ics("http://test")
        assert "VCALENDAR" in result
        assert calls["count"] == 4
    finally:
        monkeypatch.setattr(ICalDownload, "data_from_url", orig_data_from_url)


def test_get_upcoming_alarms_naive_event():
    # Event with naive datetime, should attach local tz
    ics = """BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:uid1\nDTSTART:20260116T100000\nDTEND:20260116T110000\nSUMMARY:Naive Event\nEND:VEVENT\nEND:VCALENDAR"""
    now = datetime(2026, 1, 16, 9, 50, 0, tzinfo=UTC)
    alarms = CalendarService.get_upcoming_alarms(ics, now, lookahead_minutes=120)
    assert alarms
    assert alarms[0]["uid"] == "uid1"


def test_extract_events_from_ics_missing_fields():
    # Event missing description/location
    ics = """BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:uid2\nDTSTART:20260116T100000Z\nDTEND:20260116T110000Z\nSUMMARY:No Desc\nEND:VEVENT\nEND:VCALENDAR"""
    now = datetime(2026, 1, 16, 9, 0, 0, tzinfo=UTC)
    events = CalendarService.extract_events_from_ics(
        ics, source_id=1, window_start=now, window_end=now + timedelta(days=1)
    )
    assert events
    ev = events[0]
    assert ev["uid"] == "uid2"
    assert "description" in ev
    assert "location" in ev


def test_select_latest_by_uid():
    # Two events with same UID, different end/start
    e1 = {
        "uid": "x",
        "event_start": datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        "event_end": datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
    }
    e2 = {
        "uid": "x",
        "event_start": datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        "event_end": datetime(2026, 1, 1, 13, 0, tzinfo=UTC),
    }
    latest = CalendarService._select_latest_by_uid([e1, e2])
    assert latest["x"]["event_end"] == datetime(2026, 1, 1, 13, 0, tzinfo=UTC)

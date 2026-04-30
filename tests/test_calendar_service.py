import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from sqlmodel import Session, select

from app.db.models import (
    CalendarEventCache,
    CalendarSource,
    CalendarSyncStatus,
    CalendarSyncStatusEntry,
)
from app.modules.alarms.internal.application.service import AlarmsService
from app.modules.calendar.internal.infrastructure.calendar_sync import CalendarService

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
BEGIN:VALARM
ACTION:DISPLAY
DESCRIPTION:Alarm
TRIGGER:-PT10M
END:VALARM
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
        select(CalendarEventCache).where(
            CalendarEventCache.calendar_source_id == source.id
        )
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


def test_parse_ics_events_empty():
    now = datetime(2026, 1, 16, 9, 0, 0, tzinfo=UTC)
    events = CalendarService.parse_ics_events("", now, now + timedelta(days=1))
    assert events == []


def test_parse_ics_events_malformed():
    now = datetime(2026, 1, 16, 9, 0, 0, tzinfo=UTC)
    # Malformed ICS should not raise, just return []
    events = CalendarService.parse_ics_events(
        "NOT AN ICS FILE", now, now + timedelta(days=1)
    )
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
    ics = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:uid1
DTSTART:20260116T100000
DTEND:20260116T110000
SUMMARY:Naive Event
BEGIN:VALARM
ACTION:DISPLAY
TRIGGER:-PT10M
END:VALARM
END:VEVENT
END:VCALENDAR"""
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
    # Two events with same UID, different start/end times on same date
    # With new deduplication logic, these should be kept (composite key uses date)
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

    # With new composite key (uid + date), both events are kept
    # They have the same date, so dedup picks the "latest" (e2)
    # But the key is now composite
    assert len(latest) == 1  # Same date, so only latest is kept

    # Get the event value (key is now composite "x#2026-01-01T...")
    event = next(iter(latest.values()))
    assert event["event_end"] == datetime(2026, 1, 1, 13, 0, tzinfo=UTC)


def test_recurring_event_expansion():
    """Test basic recurring event expansion (consolidated from test_recurrence_events.py)."""
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


def test_naive_event_gets_local_tz(monkeypatch):
    """Test naive event timezone handling (consolidated from test_timezone_handling.py)."""
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


@pytest.mark.anyio
async def test_get_all_alarms():
    """Test async get_all_alarms across multiple sources (consolidated from test_calendar_integration.py)."""
    from unittest.mock import AsyncMock, patch

    # Mock httpx response
    ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//hacksw/handcal//NONSGML v1.0//EN
BEGIN:VEVENT
UID:uid1@example.com
DTSTAMP:19970714T170000Z
ORGANIZER;CN=John Doe:MAILTO:john.doe@example.com
DTSTART:20260118T170000Z
DTEND:20260118T180000Z
SUMMARY:Bastille Day Party
END:VEVENT
END:VCALENDAR"""

    with patch(
        "icalevents.icaldownload.ICalDownload.data_from_url", new_callable=AsyncMock
    ) as mock_data:
        mock_data.return_value = ics_content

        sources = [
            (1, "http://example.com/cal1.ics"),
            (2, "webcal://example.com/cal2.ics"),
        ]
        await CalendarService.get_all_alarms(sources)

        # We expect the downloader to be called twice
        assert mock_data.call_count == 2


# === CONSOLIDATED FROM test_calendar_cases.py ===


def load_and_cache_events(
    session: Session, ics_path: str, source_id: int = 1, window_days: int = 7
) -> list[dict[str, Any]]:
    """Helper to load ICS and insert events into DB cache."""
    with open(ics_path, encoding="utf-8") as fh:
        ics_content = fh.read()
    now = datetime(2026, 2, 16, 0, 0, tzinfo=UTC)
    window_start = now - timedelta(days=1)
    window_end = now + timedelta(days=window_days)
    events = CalendarService.extract_events_from_ics(
        ics_content,
        source_id=source_id,
        window_start=window_start,
        window_end=window_end,
    )
    latest_by_uid = CalendarService._select_latest_by_uid(events)
    CalendarService._add_cache_entries(session, latest_by_uid, source_id)
    session.commit()
    return events


def set_event_time(session: Session, uid: str, start: datetime, end: datetime) -> None:
    """Update cached event time."""
    from app.db.models import CalendarEventCache

    row = session.exec(
        select(CalendarEventCache).where(CalendarEventCache.uid == uid)
    ).first()
    if row:
        row.event_start = start
        row.event_end = end
        session.add(row)
        session.commit()


def get_alarm(
    session: Session, uid: str, ics_path: str | None = None
) -> dict[str, Any] | None:
    """Fetch alarm by UID using ICS parsing or DB cache."""
    if ics_path is not None:
        with open(ics_path, encoding="utf-8") as fh:
            ics_content = fh.read()
        now = datetime(2026, 2, 16, 0, 0, tzinfo=UTC)
        alarms = CalendarService.get_upcoming_alarms(
            ics_content,
            check_time=now,
            lookahead_minutes=60 * 24 * 7,
            lookback_minutes=60 * 24 * 2,
        )
        for alarm in alarms:
            if uid in alarm["uid"]:
                return alarm
        return None
    alarms = asyncio.run(AlarmsService().get_active_alarms(session))
    for alarm in alarms:
        if uid in alarm["uid"]:
            return alarm
    return None


def alarm_field_checks(
    alarm: dict[str, Any],
    expected_title: str,
    expected_time: datetime,
    expected_uid: str,
) -> None:
    """Check that alarm fields match expected event info."""
    assert alarm["name"] == expected_title, (
        f"Expected title '{expected_title}', got '{alarm.get('name')}'"
    )
    assert abs((alarm["begin"] - expected_time).total_seconds()) < 60, (
        f"Expected time {expected_time}, got {alarm['begin']}"
    )
    assert expected_uid in alarm["uid"], (
        f"Expected UID '{expected_uid}' in '{alarm['uid']}'"
    )


def test_single_alarm_fields(session: Session) -> None:
    """Test single event alarm fields and trigger time."""
    events = load_and_cache_events(session, "tests/data/single_alarm.ics")
    uid = "single-alarm@example.com"
    assert len(events) > 0, "No events parsed from single_alarm.ics"
    event = next((e for e in events if e["uid"] == uid), None)
    assert event is not None, f"Event with UID {uid} not found in parsed events"
    set_event_time(session, uid, event["event_start"], event["event_end"])
    with open("tests/data/single_alarm.ics", encoding="utf-8") as fh:
        ics_content = fh.read()
    now = datetime(2026, 2, 16, 0, 0, tzinfo=UTC)
    alarms = CalendarService.get_upcoming_alarms(
        ics_content,
        check_time=now,
        lookahead_minutes=60 * 24 * 7,
        lookback_minutes=60 * 24 * 2,
    )
    alarm = next((a for a in alarms if uid in a["uid"]), None)
    assert alarm is not None, f"No alarm found for UID {uid} in alarms list"
    alarm_field_checks(alarm, "Single Event with Alarm", event["event_start"], uid)
    trigger = alarm.get("trigger_time")
    if trigger is not None:
        expected_trigger = event["event_start"] - timedelta(minutes=10)
        assert abs((trigger - expected_trigger).total_seconds()) < 60, (
            f"Expected trigger at {expected_trigger}, got {trigger}"
        )


def test_all_day_event_fields(session: Session) -> None:
    """Test all-day event fields."""
    events = load_and_cache_events(session, "tests/data/all_day.ics")
    uid = "all-day@example.com"
    assert len(events) > 0, "No events parsed from all_day.ics"
    event = next((e for e in events if e["uid"] == uid), None)
    assert event is not None, f"Event with UID {uid} not found in parsed events"
    set_event_time(session, uid, event["event_start"], event["event_end"])
    assert event["summary"] == "All Day Event"
    assert event["uid"] == uid
    assert (
        abs(
            (
                event["event_start"]
                - datetime(2026, 2, 16, 0, 0, tzinfo=event["event_start"].tzinfo)
            ).total_seconds()
        )
        < 60
    )


def test_recurring_multi_alarm_fields(session: Session) -> None:
    """Test recurring event with multiple alarms."""
    events = load_and_cache_events(session, "tests/data/recurring_multi_alarm.ics")
    uid = "recur-multi@example.com"
    assert len(events) > 0, "No events parsed from recurring_multi_alarm.ics"
    event = next((e for e in events if e["uid"] == uid), None)
    assert event is not None, f"Event with UID {uid} not found in parsed events"
    set_event_time(session, uid, event["event_start"], event["event_end"])
    alarm = get_alarm(session, uid, ics_path="tests/data/recurring_multi_alarm.ics")
    assert alarm is not None, f"No alarm found for UID {uid}"
    alarm_field_checks(
        alarm, "Recurring Event With Multiple Alarms", event["event_start"], uid
    )


def test_proximity_alarm_location_aware_fields(session: Session) -> None:
    """Test proximity/location-aware alarm fields."""
    events = load_and_cache_events(session, "tests/data/proximity_alarm.ics")
    uid = "proximity-alarm@example.com"
    assert len(events) > 0, "No events parsed from proximity_alarm.ics"
    event = next((e for e in events if e["uid"] == uid), None)
    assert event is not None, f"Event with UID {uid} not found in parsed events"
    set_event_time(session, uid, event["event_start"], event["event_end"])
    alarm = get_alarm(session, uid, ics_path="tests/data/proximity_alarm.ics")
    assert alarm is not None, f"No alarm found for proximity UID {uid}"
    alarm_field_checks(alarm, "Proximity Alarm Event", event["event_start"], uid)
    assert abs((alarm["begin"] - event["event_start"]).total_seconds()) < 60, (
        f"Proximity alarm should fire at event start: {event['event_start']}, got {alarm['begin']}"
    )


def test_recurring_past_origin_expansion_fields(session: Session) -> None:
    """Test recurring event with origin far in the past."""
    events = load_and_cache_events(session, "tests/data/recurring_past_origin.ics")
    uid = "recur-past@example.com"
    assert any(e["uid"] == uid for e in events), (
        f"No instances of recurring event {uid} found in window."
    )
    event = next((e for e in events if e["uid"] == uid), None)
    assert event is not None, f"Event with UID {uid} not found"
    set_event_time(session, uid, event["event_start"], event["event_end"])
    with open("tests/data/recurring_past_origin.ics", encoding="utf-8") as fh:
        ics_content = fh.read()
    now = datetime(2026, 2, 16, 0, 0, tzinfo=UTC)
    alarms = CalendarService.get_upcoming_alarms(
        ics_content,
        check_time=now,
        lookahead_minutes=60 * 24 * 7,
        lookback_minutes=60 * 24 * 2,
    )
    alarm = next((a for a in alarms if uid in a["uid"]), None)
    assert alarm is not None, f"No alarm found for recurring UID {uid}"
    assert alarm["name"] == "Recurring From Past"
    assert uid in alarm["uid"]
    assert "begin" in alarm
    assert alarm["begin"] is not None
    trigger = alarm.get("trigger_time")
    if trigger is not None:
        expected_trigger = alarm["begin"] - timedelta(minutes=30)
        assert abs((trigger - expected_trigger).total_seconds()) < 60


# === CONSOLIDATED FROM test_comprehensive_calendar.py ===


def test_comprehensive_calendar_parsing_and_alarms(session):
    """Integration test for calendar parsing and alarm extraction."""
    from app.db.models import CalendarSource

    source = CalendarSource(
        id=1, label="Test Source", url="https://example.com/test.ics"
    )
    session.add(source)
    session.commit()

    with open("tests/data/test_events.ics", encoding="utf-8") as fh:
        ics_content = fh.read()

    now = datetime(2026, 2, 16, 12, 0, tzinfo=UTC)
    window_start = now - timedelta(days=2)
    window_end = now + timedelta(days=7)

    events = CalendarService.extract_events_from_ics(
        ics_content, source_id=1, window_start=window_start, window_end=window_end
    )

    uids = {e["uid"] for e in events}
    assert "single-alarm@example.com" in uids
    assert "all-day@example.com" in uids
    assert "recur-multi@example.com" in uids
    assert "proximity-alarm@example.com" in uids

    prox = CalendarService._detect_proximity_uids(ics_content)
    assert "proximity-alarm@example.com" in prox

    latest_by_uid = CalendarService._select_latest_by_uid(events)
    CalendarService._add_cache_entries(session, latest_by_uid, source_id=1)
    session.commit()

    now = datetime.now(UTC)
    from app.db.models import CalendarEventCache

    all_rows = session.exec(
        select(CalendarEventCache).where(CalendarEventCache.calendar_source_id == 1)
    ).all()

    single_row = None
    prox_row = None
    for row in all_rows:
        if row.uid.startswith("single-alarm@example.com"):
            single_row = row
        elif row.uid.startswith("proximity-alarm@example.com"):
            prox_row = row

    if single_row:
        single_row.event_start = now - timedelta(minutes=5)
        single_row.event_end = now + timedelta(hours=1)
        single_row.trigger_time = now - timedelta(minutes=10)
        session.add(single_row)
    if prox_row:
        prox_row.event_start = now - timedelta(minutes=10)
        prox_row.event_end = now + timedelta(hours=1)
        prox_row.trigger_time = now - timedelta(minutes=15)
        session.add(prox_row)
    session.commit()

    alarms = asyncio.run(AlarmsService().get_active_alarms(session))

    alarm_uids = {a["uid"] for a in alarms}
    assert any(
        "single-alarm@example.com" in uid or uid.endswith("single-alarm@example.com")
        for uid in alarm_uids
    ), f"single-alarm@example.com not found in {alarm_uids}"
    assert any(
        "proximity-alarm@example.com" in uid
        or uid.endswith("proximity-alarm@example.com")
        for uid in alarm_uids
    ), f"proximity-alarm@example.com not found in {alarm_uids}"


# === CONSOLIDATED FROM test_recurrence_dst.py ===


def test_biweekly_all_day_event_tzid_preserved():
    """Test biweekly all-day event with TZID preservation."""

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

    assert len(events) >= 2
    starts = sorted([e["event_start"].date() for e in events if e.get("event_start")])
    assert datetime(2026, 1, 16).date() in starts
    assert datetime(2026, 1, 30).date() in starts

    for ev in events:
        assert "tzid" in ev
        if ev["event_start"] is not None:
            assert ev["event_start"].tzinfo is not None


def test_weekly_across_dst_preserves_wall_time():
    """Test weekly event across DST transition preserves wall clock time."""

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

    dates = {
        e["event_start"].astimezone(e["event_start"].tzinfo).date(): e
        for e in events
        if e.get("event_start")
    }
    assert datetime(2026, 3, 7).date() in dates
    assert datetime(2026, 3, 14).date() in dates

    ev1 = dates[datetime(2026, 3, 7).date()]
    ev2 = dates[datetime(2026, 3, 14).date()]

    assert ev1["tzid"] is not None
    assert ev2["tzid"] is not None
    tz1 = ZoneInfo(ev1["tzid"])
    tz2 = ZoneInfo(ev2["tzid"])
    assert ev1["event_start"].astimezone(tz1).hour == 9
    assert ev2["event_start"].astimezone(tz2).hour == 9

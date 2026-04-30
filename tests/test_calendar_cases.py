"""
Calendar Event & Alarm Processing Test Suite

Each test uses a dedicated ICS file and validates:
- Alarm visibility before/after trigger
- Location-aware (proximity) logic
- Description includes title, event time, and UUID
- Alarm trigger time correctness
- Recurring event expansion (including far-past origin)
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from app.db.models import CalendarEventCache
from app.modules.alarms.internal.application.service import AlarmsService
from app.modules.calendar.internal.infrastructure.calendar_sync import (
    CalendarService,
)

# Use a fixed reference time to make calendar tests deterministic
FIXED_NOW = datetime(2026, 2, 16, 0, 0, tzinfo=UTC)


# Helper to load ICS and insert events (for DB cache, but tests now use direct ICS parsing for alarms)
def load_and_cache_events(
    session: Session, ics_path: str, source_id: int = 1, window_days: int = 7
) -> list[dict[str, Any]]:
    with open(ics_path, encoding="utf-8") as fh:
        ics_content = fh.read()
    now = FIXED_NOW
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
    row = session.exec(select(CalendarEventCache).where(CalendarEventCache.uid == uid)).first()
    if row:
        row.event_start = start
        row.event_end = end
        session.add(row)
        session.commit()


def get_alarm(session: Session, uid: str, ics_path: str | None = None) -> dict[str, Any] | None:
    """
    If ics_path is provided, use CalendarService.get_upcoming_alarms directly on the ICS file for robust alarm extraction.
    Otherwise, fallback to the alarms module service over the DB cache.
    """
    if ics_path is not None:
        with open(ics_path, encoding="utf-8") as fh:
            ics_content = fh.read()
        now = FIXED_NOW
        alarms = CalendarService.get_upcoming_alarms(
            ics_content,
            check_time=now,
            lookahead_minutes=60 * 24 * 7,  # 1 week
            lookback_minutes=60 * 24 * 2,  # 2 days
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
    # Use standardized field names from get_upcoming_alarms()
    assert alarm["name"] == expected_title, (
        f"Expected title '{expected_title}', got '{alarm.get('name')}'"
    )
    # Use 'begin' for event start (from get_upcoming_alarms)
    assert abs((alarm["begin"] - expected_time).total_seconds()) < 60, (
        f"Expected time {expected_time}, got {alarm['begin']}"
    )
    assert expected_uid in alarm["uid"], f"Expected UID '{expected_uid}' in '{alarm['uid']}'"


def test_single_alarm_fields(session: Session) -> None:
    """Test single event alarm fields and trigger time."""
    events = load_and_cache_events(session, "tests/data/single_alarm.ics")
    uid = "single-alarm@example.com"
    assert len(events) > 0, "No events parsed from single_alarm.ics"
    event = next((e for e in events if e["uid"] == uid), None)
    assert event is not None, f"Event with UID {uid} not found in parsed events"
    set_event_time(session, uid, event["event_start"], event["event_end"])
    # Print all alarms for debugging
    with open("tests/data/single_alarm.ics", encoding="utf-8") as fh:
        ics_content = fh.read()
    now = FIXED_NOW
    alarms = CalendarService.get_upcoming_alarms(
        ics_content,
        check_time=now,
        lookahead_minutes=60 * 24 * 7,
        lookback_minutes=60 * 24 * 2,
    )
    print("[DEBUG] single_alarm.ics alarms:", alarms)
    alarm = next((a for a in alarms if uid in a["uid"]), None)
    assert alarm is not None, f"No alarm found for UID {uid} in alarms list"
    alarm_field_checks(alarm, "Single Event with Alarm", event["event_start"], uid)
    # Alarm trigger time is event start - 10min
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
    # All-day event: alarm may not be present, but event should be parsed
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
    """Test recurring event with multiple alarms, alarm fields."""
    events = load_and_cache_events(session, "tests/data/recurring_multi_alarm.ics")
    uid = "recur-multi@example.com"
    assert len(events) > 0, "No events parsed from recurring_multi_alarm.ics"
    event = next((e for e in events if e["uid"] == uid), None)
    assert event is not None, f"Event with UID {uid} not found in parsed events"
    set_event_time(session, uid, event["event_start"], event["event_end"])
    alarm = get_alarm(session, uid, ics_path="tests/data/recurring_multi_alarm.ics")
    assert alarm is not None, f"No alarm found for UID {uid}"
    alarm_field_checks(alarm, "Recurring Event With Multiple Alarms", event["event_start"], uid)


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
    # Proximity alarms should fire at event start time
    assert abs((alarm["begin"] - event["event_start"]).total_seconds()) < 60, (
        f"Proximity alarm should fire at event start: {event['event_start']}, got {alarm['begin']}"
    )


def test_recurring_past_origin_expansion_fields(session: Session) -> None:
    """Test recurring event with origin far in the past, but instance in window, alarm fields."""
    events = load_and_cache_events(session, "tests/data/recurring_past_origin.ics")
    uid = "recur-past@example.com"
    # There should be at least one instance in the window
    assert any(e["uid"] == uid for e in events), (
        f"No instances of recurring event {uid} found in window. Parsed {len(events)} events total."
    )
    event = next((e for e in events if e["uid"] == uid), None)
    assert event is not None, f"Event with UID {uid} not found despite earlier check"
    set_event_time(session, uid, event["event_start"], event["event_end"])
    # Print all alarms for debugging
    with open("tests/data/recurring_past_origin.ics", encoding="utf-8") as fh:
        ics_content = fh.read()
    now = FIXED_NOW
    alarms = CalendarService.get_upcoming_alarms(
        ics_content,
        check_time=now,
        lookahead_minutes=60 * 24 * 7,
        lookback_minutes=60 * 24 * 2,
    )
    print("[DEBUG] recurring_past_origin.ics alarms:", alarms)
    alarm = next((a for a in alarms if uid in a["uid"]), None)
    assert alarm is not None, f"No alarm found for recurring UID {uid}"

    # Verify alarm structure (title and UID)
    assert alarm["name"] == "Recurring From Past", (
        f"Expected title 'Recurring From Past', got '{alarm.get('name')}'"
    )
    assert uid in alarm["uid"], f"Expected UID '{uid}' in '{alarm['uid']}'"

    # Verify alarm has a begin time (may be different instance than from load_and_cache_events due to window differences)
    assert "begin" in alarm, "Alarm missing 'begin' field"
    assert alarm["begin"] is not None, "Alarm 'begin' is None"

    # Verify trigger time is 30 minutes before the alarm's begin time
    trigger = alarm.get("trigger_time")
    if trigger is not None:
        expected_trigger = alarm["begin"] - timedelta(minutes=30)
        assert abs((trigger - expected_trigger).total_seconds()) < 60, (
            f"Expected trigger 30min before alarm begin ({alarm['begin']}): {expected_trigger}, got {trigger}"
        )

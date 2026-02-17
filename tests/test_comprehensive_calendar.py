import asyncio
from datetime import UTC, datetime, timedelta

from sqlmodel import select

from app.services.calendar_service import CalendarService

# Fixed reference time for deterministic calendar parsing tests
FIXED_NOW = datetime(2026, 2, 16, 12, 0, tzinfo=UTC)


def test_comprehensive_calendar_parsing_and_alarms(session):
    # Create a calendar source first (required for _fetch_calendar_alarms)
    from app.db.models import CalendarSource

    source = CalendarSource(id=1, label="Test Source", url="https://example.com/test.ics")
    session.add(source)
    session.commit()

    # Load ICS test data
    with open("tests/data/test_events.ics", encoding="utf-8") as fh:
        ics_content = fh.read()

    now = FIXED_NOW
    window_start = now - timedelta(days=2)
    window_end = now + timedelta(days=7)

    # Parse events from ICS
    events = CalendarService.extract_events_from_ics(
        ics_content, source_id=1, window_start=window_start, window_end=window_end
    )

    # Expect the defined UIDs to be present in parsed events
    uids = {e["uid"] for e in events}
    assert "single-alarm@example.com" in uids
    assert "all-day@example.com" in uids
    assert "recur-multi@example.com" in uids
    assert "proximity-alarm@example.com" in uids

    # Proximity detection (string-scan) should find the proximity UID
    prox = CalendarService._detect_proximity_uids(ics_content)
    assert "proximity-alarm@example.com" in prox

    # Insert cache entries into DB using existing helper methods
    latest_by_uid = CalendarService._select_latest_by_uid(events)
    CalendarService._add_cache_entries(session, latest_by_uid, source_id=1)
    session.commit()

    # Force the single event and proximity event to be visible now
    now = datetime.now(UTC)
    # The simplest reliable approach: update by uid via raw SQL through session.get
    try:
        from app.db.models import CalendarEventCache

        single_row = session.exec(
            select(CalendarEventCache).where(CalendarEventCache.uid == "single-alarm@example.com")
        ).first()
        prox_row = session.exec(
            select(CalendarEventCache).where(
                CalendarEventCache.uid == "proximity-alarm@example.com"
            )
        ).first()
        if single_row:
            single_row.event_start = now - timedelta(minutes=5)
            single_row.event_end = now + timedelta(hours=1)
            session.add(single_row)
        if prox_row:
            prox_row.event_start = now - timedelta(minutes=10)
            prox_row.event_end = now + timedelta(hours=1)
            session.add(prox_row)
        session.commit()
    except Exception:
        # If models import fails, at least ensure the cache exists
        pass

    # Fetch alarms via the dashboard helper (which uses AlarmService.format_alarm)
    from app.routers import dashboard

    alarms = asyncio.run(dashboard._fetch_calendar_alarms(session))

    alarm_uids = {a["uid"] for a in alarms}

    # We expect the composite UID for source 1 to be present for the updated rows
    assert any(
        "single-alarm@example.com" in uid or uid.endswith("single-alarm@example.com")
        for uid in alarm_uids
    ), f"single-alarm@example.com not found in {alarm_uids}"
    assert any(
        "proximity-alarm@example.com" in uid or uid.endswith("proximity-alarm@example.com")
        for uid in alarm_uids
    ), f"proximity-alarm@example.com not found in {alarm_uids}"

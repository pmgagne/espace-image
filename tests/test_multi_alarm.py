from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import select

from app.db.models import AlarmEvent, CalendarSource
from app.modules.calendar.internal.infrastructure.calendar_sync import CalendarService


def test_check_alarm_mock(client):
    """Verify that mock=True returns multiple mock events."""
    response = client.get("/components/alarm?mock=true")
    assert response.status_code == 200
    assert "alarm-box-container" in response.text
    assert "Meeting with Client" in response.text
    assert "Dentist Appointment" in response.text
    # Verify we have three alarm items (including all-day event)
    assert response.text.count("alarm-item") == 3


def test_check_alarm_empty(client, session):
    """Verify that no alarms returns empty string."""
    # Ensure no calendar sources
    sources = session.exec(select(CalendarSource)).all()
    for s in sources:
        session.delete(s)
    session.commit()

    response = client.get("/components/alarm")
    assert response.status_code == 200
    assert response.text == ""


def test_dismiss_alarm_returns_json_status(client, session):
    """Verify dismiss command returns JSON status on the v1 alarms API."""
    # Use a valid UUID string for the alarm id to match current API parsing
    uid = "00000000-0000-0000-0000-000000000000"
    response = client.post(f"/api/v1/alarms/{uid}/dismiss")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["status"] == "dismissed"


def test_dismiss_alarm_mock_remains_mock(client, session):
    """Verify mock dismiss mode is a no-op with explicit JSON status."""
    uid = "mock-1"
    response = client.post(f"/api/v1/alarms/{uid}/dismiss?mock=true")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["status"] == "mock-noop"


@pytest.mark.anyio
async def test_get_all_alarms_namespaces_uids(monkeypatch):
    """Verify alarms from multiple calendars are namespaced by source id."""
    ics_one = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:shared-uid
SUMMARY:Calendar One
DTSTART:20260201T100000Z
DESCRIPTION:One
BEGIN:VALARM
ACTION:DISPLAY
TRIGGER:-PT10M
END:VALARM
END:VEVENT
END:VCALENDAR"""
    ics_two = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:shared-uid
SUMMARY:Calendar Two
DTSTART:20260201T100000Z
DESCRIPTION:Two
BEGIN:VALARM
ACTION:DISPLAY
TRIGGER:-PT15M
END:VALARM
END:VEVENT
END:VCALENDAR"""

    async def fake_fetch(url: str) -> str | None:
        return {"https://one": ics_one, "https://two": ics_two}.get(url)

    monkeypatch.setattr(CalendarService, "fetch_ics", fake_fetch)

    check_time = datetime(2026, 2, 1, 10, 0, tzinfo=UTC)
    alarms = await CalendarService.get_all_alarms(
        [(1, "https://one"), (2, "https://two")],
        check_time=check_time,
        lookback_minutes=60,
        lookahead_minutes=60,
    )

    uids = {alarm["uid"] for alarm in alarms}
    assert "1:shared-uid" in uids
    assert "2:shared-uid" in uids


def test_purge_old_dismissed_alarms(client, session):
    """Verify dismissed alarms older than 30 days are purged."""
    old_alarm = AlarmEvent(
        calendar_event_uid="old-dismissed",
        trigger_time=datetime.now() - timedelta(days=60),
        dismissed_at=datetime.now() - timedelta(days=31),
    )
    session.add(old_alarm)
    session.commit()

    response = client.get("/components/alarm?tz_offset=0")
    assert response.status_code == 200

    remaining = session.exec(
        select(AlarmEvent).where(AlarmEvent.calendar_event_uid == "old-dismissed")
    ).all()
    assert remaining == []

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlmodel import select

from app.db.models import AlarmEntryType, AlarmEvent, CalendarElement, CalendarSource


def test_api_get_active_alarms_returns_json_list(client):
    response = client.get("/api/v1/alarms/active")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert isinstance(response.json(), list)


def test_api_get_today_payload_returns_expected_shape(client):
    response = client.get("/api/v1/alarms/today?tz_offset=0")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    payload = response.json()
    assert "fetched_at_utc" in payload
    assert "day_start_utc" in payload
    assert "day_end_utc" in payload
    assert isinstance(payload.get("alarms"), list)
    assert isinstance(payload.get("events"), list)


def test_api_get_today_payload_uses_occurrence_start_for_alarm_display(client, session):
    """Alarm payloads should expose the event occurrence time, not the trigger time."""
    source = CalendarSource(label="Test", url="https://example.com/calendar.ics")
    session.add(source)
    session.commit()
    session.refresh(source)

    now = datetime.now(UTC).replace(microsecond=0)
    cached_start = now - timedelta(days=1)
    occurrence_start = now + timedelta(hours=2)
    occurrence_end = occurrence_start + timedelta(hours=1)
    trigger_time = occurrence_start - timedelta(minutes=15)

    session.add(
        CalendarElement(
            calendar_source_id=source.id,
            uid="occurrence-test",
            event_start=cached_start,
            event_end=cached_start + timedelta(hours=1),
            event_tz="UTC",
            summary="Occurrence Summary",
            description="",
            location="",
            all_day=False,
            trigger_time=trigger_time,
            optional_trigger=False,
            href="https://example.com/calendar/occurrence-test.ics",
            etag="etag-1",
            raw_ics="BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR\n",
        )
    )
    session.add(
        AlarmEvent(
            id=uuid4(),
            trigger_time=trigger_time,
            calendar_source_id=source.id,
            calendar_event_uid=(
                f"alarm|occurrence-test|{occurrence_start.isoformat()}|{trigger_time.isoformat()}"
            ),
            entry_type=AlarmEntryType.ALARM,
        )
    )
    session.commit()

    response = client.get("/api/v1/alarms/today?tz_offset=0")

    assert response.status_code == 200
    payload = response.json()
    matching = [alarm for alarm in payload["alarms"] if alarm["name"] == "Occurrence Summary"]
    assert len(matching) == 1
    assert matching[0]["start_iso"] == occurrence_start.isoformat()
    assert matching[0]["end_iso"] == occurrence_end.isoformat()


def test_api_create_simulated_alarm_returns_json_and_persists(client, session):
    response = client.post("/api/v1/alarms/simulated", json={"delay_seconds": 5})
    assert response.status_code == 201
    assert response.headers["content-type"].startswith("application/json")

    payload = response.json()
    assert payload["id"]

    all_alarms = session.exec(select(AlarmEvent)).all()
    assert len(all_alarms) > 0


def test_api_dismiss_alarm_updates_record(client, session):
    alarm = AlarmEvent(id=uuid4(), trigger_time=datetime.now(UTC), dismissed_at=None)
    session.add(alarm)
    session.commit()

    response = client.post(f"/api/v1/alarms/{alarm.id}/dismiss")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["status"] == "dismissed"

    session.expire_all()
    updated = session.get(AlarmEvent, alarm.id)
    assert updated is not None
    assert updated.dismissed_at is not None


def test_api_dismiss_alarm_mock_mode_is_noop(client):
    response = client.post("/api/v1/alarms/mock-1/dismiss?mock=true")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["status"] == "mock-noop"


def test_api_purge_old_endpoint_purges_dismissed_and_active_rows(client, session):
    """purge-old subsumes the retired purge-dismissed endpoint: it purges any
    stale row by trigger_time, whether dismissed or not."""
    old_dismissed = AlarmEvent(
        id=uuid4(),
        trigger_time=datetime.now(UTC) - timedelta(days=60),
        dismissed_at=datetime.now(UTC) - timedelta(days=31),
    )
    session.add(old_dismissed)
    session.commit()
    old_dismissed_id = old_dismissed.id

    response = client.post("/api/v1/alarms/purge-old")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["status"] == "purged"

    session.expire_all()
    assert session.get(AlarmEvent, old_dismissed_id) is None

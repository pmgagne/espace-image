from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlmodel import select

from app.db.models import AlarmEvent


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


def test_api_purge_old_dismissed_alarms_returns_json_and_purges(client, session):
    old_alarm = AlarmEvent(
        id=uuid4(),
        trigger_time=datetime.now(UTC) - timedelta(days=60),
        dismissed_at=datetime.now(UTC) - timedelta(days=31),
    )
    session.add(old_alarm)
    session.commit()
    old_alarm_id = old_alarm.id

    response = client.post("/api/v1/alarms/purge-dismissed")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["status"] == "purged"

    session.expire_all()
    assert session.get(AlarmEvent, old_alarm_id) is None

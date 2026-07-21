"""Tests for time-based purging of stale AlarmEvent rows."""

import importlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlmodel import Session, select

from app.db.models import AlarmEntryType, AlarmEvent
from app.main import app as fastapi_app
from app.modules.alarms.api.interfaces import get_alarms_service
from app.modules.alarms.internal.application.service import create_alarms_service
from app.modules.alarms.internal.infrastructure.repository import AlarmsRepository


def _make_alarm(*, days_offset: int, dismissed: bool = False) -> AlarmEvent:
    """Build an AlarmEvent whose trigger_time is offset from now by days."""
    now = datetime.now(UTC)
    return AlarmEvent(
        id=uuid4(),
        trigger_time=now + timedelta(days=days_offset),
        dismissed_at=now if dismissed else None,
        entry_type=AlarmEntryType.EVENT,
    )


def test_delete_triggered_before_removes_only_old_rows(session):
    cutoff = datetime.now(UTC) - timedelta(days=30)
    old = _make_alarm(days_offset=-60)
    recent = _make_alarm(days_offset=-5)
    future = _make_alarm(days_offset=5)
    session.add_all([old, recent, future])
    session.commit()

    deleted = AlarmsRepository().delete_triggered_before(session, cutoff)
    session.commit()

    assert deleted == 1
    session.expire_all()
    remaining = {alarm.id for alarm in session.exec(select(AlarmEvent)).all()}
    assert remaining == {recent.id, future.id}


@pytest.mark.anyio
async def test_purge_old_alarms_removes_only_stale_rows(session, session_factory):
    old_active = _make_alarm(days_offset=-60)
    old_dismissed = _make_alarm(days_offset=-45, dismissed=True)
    recent = _make_alarm(days_offset=-5)
    future = _make_alarm(days_offset=10)
    session.add_all([old_active, old_dismissed, recent, future])
    session.commit()

    service = create_alarms_service(session_factory, AlarmsRepository())
    deleted = await service.purge_old_alarms()

    assert deleted == 2

    session.expire_all()
    remaining = {alarm.id for alarm in session.exec(select(AlarmEvent)).all()}
    assert remaining == {recent.id, future.id}


@pytest.mark.anyio
async def test_purge_old_alarms_respects_custom_retention(session, session_factory):
    alarm = _make_alarm(days_offset=-10)
    session.add(alarm)
    session.commit()
    alarm_id = alarm.id

    service = create_alarms_service(session_factory, AlarmsRepository())

    # 30-day retention keeps a 10-day-old row.
    assert await service.purge_old_alarms(retention_days=30) == 0
    # 7-day retention purges it.
    assert await service.purge_old_alarms(retention_days=7) == 1

    session.expire_all()
    assert session.get(AlarmEvent, alarm_id) is None


def test_api_purge_old_endpoint_purges_and_reports(client, session):
    old = _make_alarm(days_offset=-60)
    future = _make_alarm(days_offset=5)
    session.add_all([old, future])
    session.commit()
    old_id = old.id
    future_id = future.id

    response = client.post("/api/v1/alarms/purge-old")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "purged"
    assert body["deleted"] == 1

    session.expire_all()
    assert session.get(AlarmEvent, old_id) is None
    assert session.get(AlarmEvent, future_id) is not None


def test_alarm_retention_days_clamped_to_minimum_one(monkeypatch):
    """0 or a negative ALARM_RETENTION_DAYS would put the purge cutoff at or
    after "now", deleting currently-displayed or not-yet-fired alarms."""
    cfg = importlib.import_module("app.config")
    try:
        for raw_value in ("0", "-7"):
            monkeypatch.setenv("ALARM_RETENTION_DAYS", raw_value)
            importlib.reload(cfg)
            assert cfg.ALARM_RETENTION_DAYS == 1
    finally:
        monkeypatch.delenv("ALARM_RETENTION_DAYS", raising=False)
        importlib.reload(cfg)


class _FailingAlarmsRepository(AlarmsRepository):
    """Repository double that always fails, to exercise purge error paths."""

    def delete_triggered_before(self, session: Session, cutoff: datetime) -> int:
        raise RuntimeError("simulated database failure")


@pytest.mark.anyio
async def test_purge_old_alarms_propagates_failure(session_factory):
    """A DB failure during purge must not be reported as "0 rows purged" —
    callers need to distinguish "nothing to purge" from "the purge failed"."""
    service = create_alarms_service(session_factory, _FailingAlarmsRepository())

    with pytest.raises(RuntimeError):
        await service.purge_old_alarms()


def test_api_purge_old_endpoint_returns_500_on_failure(client, session_factory):
    fastapi_app.dependency_overrides[get_alarms_service] = lambda: create_alarms_service(
        session_factory, _FailingAlarmsRepository()
    )

    response = client.post("/api/v1/alarms/purge-old")

    assert response.status_code == 500
    assert response.json()["status"] == "error"

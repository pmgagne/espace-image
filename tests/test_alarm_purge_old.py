"""Tests for time-based purging of stale AlarmEvent rows."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlmodel import select

from app.db.models import AlarmEntryType, AlarmEvent
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


def test_list_triggered_before_returns_only_old_rows(session):
    cutoff = datetime.now(UTC) - timedelta(days=30)
    old = _make_alarm(days_offset=-60)
    recent = _make_alarm(days_offset=-5)
    future = _make_alarm(days_offset=5)
    session.add_all([old, recent, future])
    session.commit()

    result = AlarmsRepository().list_triggered_before(session, cutoff)

    ids = {alarm.id for alarm in result}
    assert ids == {old.id}


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

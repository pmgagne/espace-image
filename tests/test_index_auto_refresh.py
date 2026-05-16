from datetime import UTC, datetime
from uuid import uuid4


def test_index_refresh_includes_simulated_alarm(client, session):
    """`/components/index-refresh` should no longer carry alarm fragments."""

    resp = client.get("/components/index-refresh")
    assert resp.status_code == 200
    assert "Simulated Event" not in resp.text

    # Insert a simulated AlarmEvent (no calendar link) with trigger_time <= now
    from app.db.models import AlarmEvent

    now_naive = datetime.now(UTC).replace(tzinfo=None)
    alarm = AlarmEvent(
        id=uuid4(),
        trigger_time=now_naive,
        dismissed_at=None,
        calendar_source_id=None,
        calendar_event_uid=None,
    )
    session.add(alarm)
    session.commit()

    # Index refresh remains alarm-free; alarm rendering is handled separately.
    resp2 = client.get("/components/index-refresh")
    assert resp2.status_code == 200
    assert "Simulated Event" not in resp2.text

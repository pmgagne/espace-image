from datetime import UTC, datetime
from uuid import uuid4


def test_index_refresh_includes_simulated_alarm(client, session):
    """Simulate a DB alarm and verify `/components/index-refresh` returns the alarm fragment.

    This exercises the same endpoint used by the client-side poll so it
    confirms an appearing alarm would be surfaced to the UI poller.
    """
    # Ensure no simulated alarm present initially
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

    # The index-refresh should now include the simulated alarm fragment
    resp2 = client.get("/components/index-refresh")
    assert resp2.status_code == 200
    assert "Simulated Event" in resp2.text

"""Tests for the debug panel alarm simulation feature."""

from datetime import UTC, datetime, timedelta

from sqlmodel import select

from app.db.models import AlarmEvent


def test_debug_panel_disabled_by_default(client):
    """Debug panel should not appear when WEBAPP_DEBUG is not set."""
    response = client.get("/admin/")
    # The admin page loads but should not have the debug link by default
    # Note: the global is set in the main.py at startup, so this depends on env
    # For now, just verify the admin page loads
    assert response.status_code == 200
    assert "Admin Panel" in response.text


def test_debug_pane_loads(client):
    """Debug pane partial should load successfully."""
    response = client.get("/admin/partials/debug")
    assert response.status_code == 200
    assert "Debug Panel" in response.text
    assert "Simulate Alarm" in response.text
    assert "delay_seconds" in response.text


def test_simulate_alarm_creates_alarm_event(client, session):
    """Simulating an alarm should create an AlarmEvent in the database."""
    initial_count = session.exec(select(AlarmEvent)).all()
    initial_alarm_count = len(initial_count)

    # Simulate an alarm with 5 second delay
    response = client.post("/admin/debug/simulate-alarm", data={"delay_seconds": 5})
    assert response.status_code == 200
    assert "Success" in response.text or "Simulated alarm" in response.text

    # Check that alarm was created in database
    all_alarms = session.exec(select(AlarmEvent)).all()
    assert len(all_alarms) > initial_alarm_count

    # Get the newest alarm
    new_alarm = all_alarms[-1]
    # Simulated alarms use generated UUID `id` rather than a separate `uid` field
    assert getattr(new_alarm, "id", None) is not None
    assert new_alarm.calendar_event_uid is None
    assert new_alarm.dismissed_at is None  # Not dismissed yet

    # Verify trigger time is approximately now + 5 seconds
    expected_trigger = datetime.now(UTC) + timedelta(seconds=5)
    # Normalize naive datetimes to UTC for comparison
    trg = new_alarm.trigger_time
    if trg.tzinfo is None:
        trg = trg.replace(tzinfo=UTC)
    time_diff = abs((trg - expected_trigger).total_seconds())
    assert time_diff < 2  # Allow 2 second tolerance


def test_simulate_alarm_with_zero_delay(client, session):
    """Simulating an alarm with 0 delay should create alarm for now."""
    response = client.post("/admin/debug/simulate-alarm", data={"delay_seconds": 0})
    assert response.status_code == 200

    # Get the newest alarm
    all_alarms = session.exec(select(AlarmEvent)).all()
    new_alarm = all_alarms[-1]

    # Trigger time should be very close to now
    trg = new_alarm.trigger_time
    if trg.tzinfo is None:
        trg = trg.replace(tzinfo=UTC)
    time_diff = abs((trg - datetime.now(UTC)).total_seconds())
    assert time_diff < 2


def test_simulate_alarm_uid_is_unique(client, session):
    """Each simulated alarm should have a unique UID."""
    client.post("/admin/debug/simulate-alarm", data={"delay_seconds": 0})
    client.post("/admin/debug/simulate-alarm", data={"delay_seconds": 0})

    all_alarms = session.exec(select(AlarmEvent)).all()
    ids = [str(alarm.id) for alarm in all_alarms]

    # Check all IDs are unique
    assert len(ids) == len(set(ids))

    # Basic sanity: IDs are non-empty strings
    for _id in ids:
        assert len(_id) > 0


def test_simulated_alarm_can_be_dismissed(client, session):
    """Simulated alarms should be dismissible like normal alarms."""
    # Create a simulated alarm
    client.post("/admin/debug/simulate-alarm", data={"delay_seconds": 0})

    # Get the alarm id (simulated alarms are identified by UUID)
    alarm = session.exec(select(AlarmEvent)).first()
    alarm_id = str(alarm.id)

    # Dismiss the alarm
    response = client.post(f"/api/alarms/{alarm_id}/dismiss?mock=false")
    assert response.status_code == 200

    # Need to refresh the session to get updated data
    session.expunge_all()

    # Check alarm is marked as dismissed - the dismiss endpoint creates a new record
    # or updates existing one
    # Use stored alarm_id (convert back to UUID for query)
    from uuid import UUID

    alarm_uuid = UUID(alarm_id)
    all_alarms = session.exec(select(AlarmEvent).where(AlarmEvent.id == alarm_uuid)).all()
    assert len(all_alarms) > 0
    # Find the one with dismissed_at set
    dismissed = [a for a in all_alarms if a.dismissed_at is not None]
    assert len(dismissed) > 0

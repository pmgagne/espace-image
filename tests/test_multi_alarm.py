from sqlmodel import select

from app.db.models import CalendarSource


def test_check_alarm_mock(client):
    """Verify that mock=True returns multiple mock events."""
    response = client.get("/components/alarm?mock=true")
    assert response.status_code == 200
    assert "alarm-box-container" in response.text
    assert "Meeting with Client" in response.text
    assert "Dentist Appointment" in response.text
    # Verify we have at least two alarm items
    assert response.text.count("alarm-item") == 2


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


def test_dismiss_alarm_returns_updated_html(client, session):
    """Verify that dismissing an alarm returns the updated alarm list HTML."""
    uid = "test-uid-123"
    response = client.post(f"/api/alarms/{uid}/dismiss")
    assert response.status_code == 200
    # Should return empty string if no alarms left, or the container if some remain.
    # In this empty test environment, it should be empty string because no sources are set.
    assert response.text == ""


def test_dismiss_alarm_mock_remains_mock(client, session):
    """Verify that dismissing a mock alarm returns mock data."""
    uid = "mock-1"
    response = client.post(f"/api/alarms/{uid}/dismiss?mock=true")
    assert response.status_code == 200
    assert "alarm-box-container" in response.text
    assert "Dentist Appointment" in response.text

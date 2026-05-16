import pytest


def test_read_root(client):
    """Test the root endpoint returns 200 and the index template."""
    response = client.get("/")
    assert response.status_code == 200
    # Check for expected content from templates/index.html
    assert "Espace-Image" in response.text


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_background_sync_calendars_runs_general_sync(monkeypatch):
    """Background scheduler callback should run calendar general sync."""
    from app import main

    class DummyCalendarService:
        def __init__(self) -> None:
            self.called = False

        async def general_sync(self):
            self.called = True

            class Result:
                alarms_skipped = True
                alarms_skip_reason = "test"
                normalized_alarm_count = 0

            return Result()

    dummy_service = DummyCalendarService()

    monkeypatch.setattr(main, "build_calendar_service", lambda _session_factory: dummy_service)

    await main.background_sync_calendars()

    assert dummy_service.called is True

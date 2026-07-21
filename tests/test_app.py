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


class _DummyAlarmsService:
    def __init__(self) -> None:
        self.purge_called = False

    async def purge_old_alarms(self):
        self.purge_called = True
        return 0


@pytest.mark.anyio
async def test_background_sync_purges_alarms_even_with_no_calendar_sources(monkeypatch):
    """The alarm-retention purge must run even when there are no configured
    calendar sources, otherwise stale rows never get cleaned up on an
    instance with no calendars configured."""
    from app import main

    class DummyCalendarService:
        def __init__(self) -> None:
            self.general_sync_called = False

        async def get_calendars_for_ui(self):
            return {"sources": []}

        async def general_sync(self):
            self.general_sync_called = True

            class Result:
                alarms_skipped = True
                alarms_skip_reason = "test"
                normalized_alarm_count = 0

            return Result()

    dummy_calendar_service = DummyCalendarService()
    dummy_alarms_service = _DummyAlarmsService()

    monkeypatch.setattr(
        main, "build_calendar_service", lambda _session_factory: dummy_calendar_service
    )
    monkeypatch.setattr(main, "build_alarms_service", lambda _session_factory: dummy_alarms_service)

    await main.background_sync_calendars()

    assert dummy_calendar_service.general_sync_called is False
    assert dummy_alarms_service.purge_called is True


@pytest.mark.anyio
async def test_background_sync_purges_alarms_even_when_general_sync_fails(monkeypatch):
    """The alarm-retention purge must run even when calendar sync itself
    raises (e.g. an unreachable CalDAV server), otherwise a persistently
    failing sync silently disables the purge forever."""
    from app import main

    class DummyCalendarService:
        async def general_sync(self):
            raise RuntimeError("simulated sync failure")

    dummy_alarms_service = _DummyAlarmsService()

    monkeypatch.setattr(
        main, "build_calendar_service", lambda _session_factory: DummyCalendarService()
    )
    monkeypatch.setattr(main, "build_alarms_service", lambda _session_factory: dummy_alarms_service)

    await main.background_sync_calendars()

    assert dummy_alarms_service.purge_called is True

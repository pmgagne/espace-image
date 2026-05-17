import importlib


def test_fetch_caldav_disabled(monkeypatch):
    """When CalDAV is disabled via config, the adapter returns None quickly."""
    cfg = importlib.import_module("app.config")
    monkeypatch.setattr(cfg, "CALDAV_SYNC_ENABLED", False)
    # Ensure other vars are empty so function exits early
    monkeypatch.setattr(cfg, "CALDAV_URL", "")
    monkeypatch.setattr(cfg, "CALDAV_CALENDAR", "")

    client = importlib.import_module("app.modules.calendar.internal.infrastructure.caldav_client")
    # Call the async function via asyncio
    import asyncio

    res = asyncio.run(client.fetch_caldav_calendar_ics())
    assert res is None


def test_fetch_caldav_import_error(monkeypatch):
    """If caldav library is not installed, adapter logs warning and returns None."""
    cfg = importlib.import_module("app.config")
    monkeypatch.setattr(cfg, "CALDAV_SYNC_ENABLED", True)
    monkeypatch.setattr(cfg, "CALDAV_URL", "https://example.com/dav")
    monkeypatch.setattr(cfg, "CALDAV_CALENDAR", "/calendars/user/calendar")

    # Ensure caldav is not importable by removing from sys.modules and
    # simulating ImportError on import by using monkeypatch to delete if present
    import sys

    sys.modules.pop("caldav", None)

    client = importlib.import_module("app.modules.calendar.internal.infrastructure.caldav_client")
    import asyncio

    res = asyncio.run(client.fetch_caldav_calendar_ics())
    assert res is None


def test_fetch_caldav_matches_object_href(monkeypatch):
    """CalDAV matching should work even if calendar href is not a plain string."""
    client = importlib.import_module("app.modules.calendar.internal.infrastructure.caldav_client")

    monkeypatch.setattr(client, "CALDAV_SYNC_ENABLED", True)
    monkeypatch.setattr(client, "CALDAV_URL", "https://caldav.icloud.com")
    monkeypatch.setattr(client, "CALDAV_USERNAME", "user@example.com")
    monkeypatch.setattr(client, "CALDAV_PASSWORD", "secret")

    class _Href:
        def __str__(self):
            return "https://caldav.icloud.com/143709226/calendars/ABC123/"

    class _Event:
        data = "BEGIN:VEVENT\nSUMMARY:demo\nEND:VEVENT"

    class _SyncCollection:
        sync_token = "token-1"

        def __len__(self):
            return 1

    class _Calendar:
        url = _Href()

        def get_objects_by_sync_token(self, sync_token=None):
            return _SyncCollection()

        def events(self):
            return [_Event()]

    class _Principal:
        def calendars(self):
            return [_Calendar()]

    class _Client:
        def principal(self):
            return _Principal()

    monkeypatch.setattr(client.caldav, "DAVClient", lambda **_: _Client())

    import asyncio

    result = asyncio.run(
        client.fetch_caldav_calendar_ics(
            calendar_url="https://caldav.icloud.com/143709226/calendars/ABC123/"
        )
    )

    assert result is not None
    assert "BEGIN:VCALENDAR" in result
    assert "SUMMARY:demo" in result


def test_fetch_caldav_with_sync_token_no_changes(monkeypatch):
    """No-change sync-token fetch should skip full event download."""
    client = importlib.import_module("app.modules.calendar.internal.infrastructure.caldav_client")

    monkeypatch.setattr(client, "CALDAV_SYNC_ENABLED", True)
    monkeypatch.setattr(client, "CALDAV_URL", "https://caldav.icloud.com")
    monkeypatch.setattr(client, "CALDAV_USERNAME", "user@example.com")
    monkeypatch.setattr(client, "CALDAV_PASSWORD", "secret")

    class _Href:
        def __str__(self):
            return "https://caldav.icloud.com/143709226/calendars/ABC123/"

    class _SyncCollection:
        sync_token = "token-next"

        def __len__(self):
            return 0

    class _Calendar:
        url = _Href()

        def get_objects_by_sync_token(self, sync_token=None):
            return _SyncCollection()

        def events(self):
            raise AssertionError("events() should not be called when there are no changes")

    class _Principal:
        def calendars(self):
            return [_Calendar()]

    class _Client:
        def principal(self):
            return _Principal()

    monkeypatch.setattr(client.caldav, "DAVClient", lambda **_: _Client())

    import asyncio

    result = asyncio.run(
        client.fetch_caldav_calendar_ics_with_metadata(
            calendar_url="https://caldav.icloud.com/143709226/calendars/ABC123/",
            sync_token="token-prev",
        )
    )

    assert result.content is None
    assert result.changed is False
    assert result.sync_token == "token-next"
    assert result.fetch_succeeded is True


def test_fetch_caldav_calendars_with_metadata_reuses_one_authenticated_context(monkeypatch):
    """Batch fetch should reuse one DAV client/principal lookup for multiple calendars."""
    client = importlib.import_module("app.modules.calendar.internal.infrastructure.caldav_client")

    monkeypatch.setattr(client, "CALDAV_SYNC_ENABLED", True)
    monkeypatch.setattr(client, "CALDAV_URL", "https://caldav.icloud.com")
    monkeypatch.setattr(client, "CALDAV_USERNAME", "user@example.com")
    monkeypatch.setattr(client, "CALDAV_PASSWORD", "secret")

    calls = {"dav_client": 0, "principal": 0}

    class _SyncCollection:
        def __init__(self, token):
            self.sync_token = token

        def __len__(self):
            return 1

    class _Event:
        def __init__(self, href, summary):
            self.url = href
            self.etag = summary
            self.data = f"BEGIN:VEVENT\nUID:{summary}\nSUMMARY:{summary}\nEND:VEVENT"

    class _Calendar:
        def __init__(self, href, summary):
            self.url = href
            self._summary = summary

        def get_objects_by_sync_token(self, sync_token=None):
            del sync_token
            return _SyncCollection(f"token-{self._summary}")

        def events(self):
            return [_Event(f"{self.url}event.ics", self._summary)]

    class _Principal:
        def calendars(self):
            calls["principal"] += 1
            return [
                _Calendar("https://caldav.icloud.com/calendars/work/", "work"),
                _Calendar("https://caldav.icloud.com/calendars/home/", "home"),
            ]

    class _Client:
        def principal(self):
            return _Principal()

    def _build_client(**_kwargs):
        calls["dav_client"] += 1
        return _Client()

    monkeypatch.setattr(client.caldav, "DAVClient", _build_client)

    import asyncio

    results = asyncio.run(
        client.fetch_caldav_calendars_with_metadata(
            [
                ("https://caldav.icloud.com/calendars/work/", None),
                ("https://caldav.icloud.com/calendars/home/", None),
            ]
        )
    )

    assert calls["dav_client"] == 1
    assert calls["principal"] == 1
    assert results["https://caldav.icloud.com/calendars/work/"].fetch_succeeded is True
    assert results["https://caldav.icloud.com/calendars/home/"].fetch_succeeded is True
    assert "SUMMARY:work" in (results["https://caldav.icloud.com/calendars/work/"].content or "")
    assert "SUMMARY:home" in (results["https://caldav.icloud.com/calendars/home/"].content or "")


def test_fetch_caldav_fail_on_error_raises(monkeypatch):
    """Strict mode should raise on authenticated CalDAV failures."""
    client = importlib.import_module("app.modules.calendar.internal.infrastructure.caldav_client")

    monkeypatch.setattr(client, "CALDAV_SYNC_ENABLED", True)
    monkeypatch.setattr(client, "CALDAV_URL", "https://caldav.icloud.com")
    monkeypatch.setattr(client, "CALDAV_USERNAME", "user@example.com")
    monkeypatch.setattr(client, "CALDAV_PASSWORD", "secret")
    monkeypatch.setattr(client, "CALDAV_MAX_RETRIES", 1)

    class _Client:
        def principal(self):
            raise TimeoutError("timed out")

    monkeypatch.setattr(client.caldav, "DAVClient", lambda **_: _Client())

    import asyncio

    try:
        asyncio.run(
            client.fetch_caldav_calendar_ics(
                calendar_url="https://caldav.icloud.com/143709226/calendars/ABC123/",
                fail_on_error=True,
            )
        )
        raise AssertionError("Expected CalDAVFetchError")
    except client.CalDAVFetchError:
        pass

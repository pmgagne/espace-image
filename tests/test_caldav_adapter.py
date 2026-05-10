import importlib

import pytest


def test_fetch_caldav_disabled(monkeypatch):
    """When CalDAV is disabled via config, the adapter returns None quickly."""
    cfg = importlib.import_module("app.config")
    monkeypatch.setattr(cfg, "CALDAV_SYNC_ENABLED", False)
    # Ensure other vars are empty so function exits early
    monkeypatch.setattr(cfg, "CALDAV_URL", "")
    monkeypatch.setattr(cfg, "CALDAV_CALENDAR", "")

    client = importlib.import_module(
        "app.modules.calendar.internal.infrastructure.caldav_client"
    )
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

    client = importlib.import_module(
        "app.modules.calendar.internal.infrastructure.caldav_client"
    )
    import asyncio

    res = asyncio.run(client.fetch_caldav_calendar_ics())
    assert res is None

"""Tests for espima CLI command surface and selectors."""

from dataclasses import dataclass
from datetime import UTC, datetime

from typer.testing import CliRunner

from espima import cli

runner = CliRunner()


@dataclass
class DummySource:
    """Simple DTO for created calendar sources in tests."""

    id: int
    label: str
    url: str
    color: str


class DummyCalendarService:
    """Minimal async service mock for espima calendar commands."""

    def __init__(self) -> None:
        self.sources: list[DummySource] = []
        self.synced = False
        self.normalized_count = 0

    async def get_calendars_for_ui(self) -> dict[str, list[DummySource]]:
        return {"sources": self.sources}

    async def create_source(self, label: str, url: str, color: str) -> DummySource:
        source = DummySource(id=len(self.sources) + 1, label=label, url=url, color=color)
        self.sources.append(source)
        return source

    async def delete_source(self, source_id: int) -> bool:
        for idx, source in enumerate(self.sources):
            if source.id == source_id:
                del self.sources[idx]
                return True
        return False

    async def sync_calendars(self) -> None:
        self.synced = True

    async def normalize_alarm_occurrences(self) -> int:
        self.normalized_count += 1
        return 7

    async def get_sync_status(self) -> list[object]:
        @dataclass
        class Status:
            calendar_source_id: int
            sync_status: str
            last_synced_at: datetime | None
            error_count: int
            event_count: int

        return [
            Status(
                calendar_source_id=1,
                sync_status="success",
                last_synced_at=None,
                error_count=0,
                event_count=3,
            )
        ]


def test_root_help_shows_command_groups() -> None:
    """CLI help should expose db and caldav groups."""
    result = runner.invoke(cli.app, ["--help"])

    assert result.exit_code == 0
    assert "db" in result.stdout
    assert "caldav" in result.stdout


def test_db_init_calls_init_db(monkeypatch) -> None:
    """db init should call init_db.init exactly once."""
    calls = {"count": 0}

    def fake_initialize_database() -> None:
        calls["count"] += 1

    monkeypatch.setattr("espima.cli._initialize_database", fake_initialize_database)

    result = runner.invoke(cli.app, ["db", "init"])

    assert result.exit_code == 0
    assert calls["count"] == 1


def test_db_migrate_calls_alembic_upgrade(monkeypatch) -> None:
    """db migrate should invoke alembic upgrade head."""
    calls: list[str] = []

    def fake_upgrade(_cfg, rev: str) -> None:
        calls.append(rev)

    monkeypatch.setattr("espima.cli.command.upgrade", fake_upgrade)

    result = runner.invoke(cli.app, ["db", "migrate"])

    assert result.exit_code == 0
    assert calls == ["head"]


def test_caldav_add_uses_index_selector(monkeypatch) -> None:
    """caldav add should resolve and add selected calendar by index."""
    service = DummyCalendarService()

    monkeypatch.setattr("espima.cli._build_calendar_service", lambda: service)
    monkeypatch.setattr(
        "espima.cli._discover_remote_calendars",
        lambda *_args: [
            cli.RemoteCalendar(guid="a-guid", name="Work", url="https://cal.example/work"),
            cli.RemoteCalendar(guid="b-guid", name="Home", url="https://cal.example/home"),
        ],
    )

    result = runner.invoke(
        cli.app,
        [
            "caldav",
            "add",
            "--index",
            "2",
            "--url",
            "https://cal.example",
        ],
    )

    assert result.exit_code == 0
    assert len(service.sources) == 1
    assert service.sources[0].label == "Home"


def test_caldav_sync_runs_service(monkeypatch) -> None:
    """caldav sync should run sync and print status rows."""
    service = DummyCalendarService()
    monkeypatch.setattr("espima.cli._build_calendar_service", lambda: service)

    result = runner.invoke(cli.app, ["caldav", "sync"])

    assert result.exit_code == 0
    assert service.synced is True


def test_caldav_normalize_alarms_runs_service(monkeypatch) -> None:
    """caldav normalize-alarms should invoke normalization pipeline."""
    service = DummyCalendarService()
    monkeypatch.setattr("espima.cli._build_calendar_service", lambda: service)

    result = runner.invoke(cli.app, ["caldav", "normalize-alarms"])

    assert result.exit_code == 0
    assert service.normalized_count == 1
    assert "Normalized alarm occurrences" in result.stdout


def test_caldav_added_lists_db_sources(monkeypatch) -> None:
    """caldav added should list sources currently configured in DB service."""
    service = DummyCalendarService()
    service.sources = [
        DummySource(id=1, label="Work", url="https://cal.example/work", color="#3182ce")
    ]
    monkeypatch.setattr("espima.cli._build_calendar_service", lambda: service)

    result = runner.invoke(cli.app, ["caldav", "added"])

    assert result.exit_code == 0
    assert "Configured calendars" in result.stdout
    assert "Work" in result.stdout


def test_caldav_remove_deletes_existing_source(monkeypatch) -> None:
    """caldav remove should delete source by ID."""
    service = DummyCalendarService()
    service.sources = [
        DummySource(id=1, label="Work", url="https://cal.example/work", color="#3182ce")
    ]
    monkeypatch.setattr("espima.cli._build_calendar_service", lambda: service)

    result = runner.invoke(cli.app, ["caldav", "remove", "1"])

    assert result.exit_code == 0
    assert len(service.sources) == 0
    assert "Removed calendar source" in result.stdout


def test_caldav_remove_returns_error_for_missing_source(monkeypatch) -> None:
    """caldav remove should fail when ID does not exist."""
    service = DummyCalendarService()
    monkeypatch.setattr("espima.cli._build_calendar_service", lambda: service)

    result = runner.invoke(cli.app, ["caldav", "remove", "99"])

    assert result.exit_code == 1
    assert "No calendar found" in result.stdout


def test_format_user_facing_datetime_uses_default_timezone(monkeypatch) -> None:
    """Displayed timestamps should use DEFAULT_TIMEZONE."""
    monkeypatch.setenv("DEFAULT_TIMEZONE", "America/Toronto")

    value = datetime(2026, 5, 14, 1, 0, tzinfo=UTC)
    rendered = cli._format_user_facing_datetime(value)

    assert rendered.endswith("-04:00")


def test_format_user_facing_datetime_invalid_timezone_falls_back_utc(monkeypatch) -> None:
    """Invalid timezone names should fall back to UTC output."""
    monkeypatch.setenv("DEFAULT_TIMEZONE", "Invalid/Zone")

    value = datetime(2026, 5, 14, 1, 0, tzinfo=UTC)
    rendered = cli._format_user_facing_datetime(value)

    assert rendered.endswith("+00:00")

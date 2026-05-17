"""Tests for espima CLI command surface and selectors."""

from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlmodel import Session, select
from typer.testing import CliRunner

from app.db.models import AlarmEvent, CalendarElement, CalendarSource
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
        self.last_normalize_start_date: date | None = None
        self.last_normalize_days = 0
        self.general_sync_called = False

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

    async def normalize_alarm_occurrences(
        self,
        start_date: date | None = None,
        days: int = 30,
    ) -> int:
        self.normalized_count += 1
        self.last_normalize_start_date = start_date
        self.last_normalize_days = days
        return 7

    async def general_sync(
        self,
        start_date: date | None = None,
        days: int = 30,
    ) -> object:
        self.general_sync_called = True
        self.last_normalize_start_date = start_date
        self.last_normalize_days = days

        @dataclass
        class Result:
            calendar_sync_success: bool
            alarms_sync_success: bool
            alarms_skipped: bool
            alarms_skip_reason: str | None
            normalized_alarm_count: int

        return Result(
            calendar_sync_success=True,
            alarms_sync_success=True,
            alarms_skipped=False,
            alarms_skip_reason=None,
            normalized_alarm_count=7,
        )

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


class DummyAlarmsService:
    """Minimal async service mock for espima alarms commands."""

    async def get_debug_alarm_state(self) -> dict[str, list[dict[str, str | int | None]]]:
        return {
            "alarm_events": [
                {
                    "id": "alarm-1",
                    "calendar_source_id": 1,
                    "calendar_event_uid": "uid-1",
                    "trigger_time": "2026-01-15T09:45:00+00:00",
                    "dismissed_at": None,
                }
            ]
        }


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


def test_db_clear_calendars_calls_clear_helper(monkeypatch) -> None:
    """db clear calendars should clear cached calendar rows and report counts."""
    monkeypatch.setattr("espima.cli._clear_calendar_cache", lambda: (3, 5))

    result = runner.invoke(cli.app, ["db", "clear", "calendars"])

    assert result.exit_code == 0
    assert "calendar_elements=3" in result.stdout
    assert "alarmevent=5" in result.stdout


def test_clear_calendar_cache_preserves_sources(session) -> None:
    """Low-level cache clearing should remove cached rows without deleting sources."""
    engine = session.get_bind()

    with Session(engine) as session:
        source = CalendarSource(label="Keep", url="https://example.com/calendar.ics")
        session.add(source)
        session.commit()
        session.refresh(source)

        session.add(
            CalendarElement(
                calendar_source_id=source.id,
                uid="uid-1",
                summary="Keep source",
                href="",
                raw_ics="BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR\n",
            )
        )
        session.add(AlarmEvent(trigger_time=datetime.now(UTC), calendar_source_id=source.id))
        session.commit()

    cleared_elements, cleared_alarms = cli._clear_calendar_cache(engine)

    with Session(engine) as session:
        assert cleared_elements == 1
        assert cleared_alarms == 1
        assert session.exec(select(CalendarSource)).all()
        assert session.exec(select(CalendarElement)).all() == []
        assert session.exec(select(AlarmEvent)).all() == []


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


def test_alarms_sync_runs_service(monkeypatch) -> None:
    """alarms sync should invoke normalization pipeline."""
    service = DummyCalendarService()
    monkeypatch.setattr("espima.cli._build_calendar_service", lambda: service)

    result = runner.invoke(
        cli.app,
        [
            "alarms",
            "sync",
            "--start-date",
            "2026-01-15",
            "--days",
            "14",
        ],
    )

    assert result.exit_code == 0
    assert service.normalized_count == 1
    assert service.last_normalize_start_date == date(2026, 1, 15)
    assert service.last_normalize_days == 14
    assert "Normalized alarm occurrences" in result.stdout


def test_sync_runs_general_sync(monkeypatch) -> None:
    """top-level sync should call general sync with parsed alarm window."""
    service = DummyCalendarService()
    monkeypatch.setattr("espima.cli._build_calendar_service", lambda: service)

    result = runner.invoke(
        cli.app,
        [
            "sync",
            "--start-date",
            "2026-01-15",
            "--days",
            "14",
        ],
    )

    assert result.exit_code == 0
    assert service.general_sync_called is True
    assert service.last_normalize_start_date == date(2026, 1, 15)
    assert service.last_normalize_days == 14
    assert "General sync completed" in result.stdout


def test_alarms_list_shows_rows(monkeypatch) -> None:
    """alarms list should render alarm events stored in DB state."""
    service = DummyAlarmsService()
    monkeypatch.setattr("espima.cli._build_alarms_service", lambda: service)

    result = runner.invoke(cli.app, ["alarms", "list"])

    assert result.exit_code == 0
    assert "Alarm events" in result.stdout
    assert "alarm-1" in result.stdout


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

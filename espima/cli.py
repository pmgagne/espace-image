"""Espima CLI entrypoint for database and CalDAV workflows."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, tzinfo
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import typer
from alembic.config import Config
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from alembic import command

load_dotenv()

console = Console()
app = typer.Typer(help="Project management CLI for espace-image.", no_args_is_help=True)
db_app = typer.Typer(help="Database commands.", no_args_is_help=True)
caldav_app = typer.Typer(help="CalDAV commands.", no_args_is_help=True)
alarms_app = typer.Typer(
    help="Alarm and event processing commands.",
    no_args_is_help=True,
)
app.add_typer(db_app, name="db")
app.add_typer(caldav_app, name="caldav")
app.add_typer(alarms_app, name="alarms")


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", help="Show espima package location and exit."),
) -> None:
    """Top-level CLI callback."""
    if version:
        console.print(f"espima available at {Path(__file__).resolve().parent}")
        raise typer.Exit(code=0)


@dataclass(frozen=True)
class RemoteCalendar:
    """Remote calendar descriptor discovered from a CalDAV account."""

    guid: str
    name: str
    url: str


def _repo_root() -> Path:
    """Return repository root for locating alembic.ini from installed package code."""
    return Path(__file__).resolve().parent.parent


def _build_calendar_service() -> Any:
    """Build calendar service using the app's module composition wiring."""
    from app.db.engine import engine
    from app.db.session_factory import SessionFactory
    from app.modules.calendar.loader import build_calendar_service

    return build_calendar_service(SessionFactory(engine))


def _build_alarms_service() -> Any:
    """Build alarms service using the app's module composition wiring."""
    from app.db.engine import engine
    from app.db.session_factory import SessionFactory
    from app.modules.alarms.internal.application.service import create_alarms_service
    from app.modules.alarms.internal.infrastructure.repository import AlarmsRepository

    return create_alarms_service(
        SessionFactory(engine),
        AlarmsRepository(),
    )


def _initialize_database() -> None:
    """Initialize tables and seed default settings rows."""
    from sqlmodel import Session, select

    from app.db.engine import create_db_and_tables, engine
    from app.db.models import AppSettings, Preset

    create_db_and_tables()
    with Session(engine) as session:
        preset = session.exec(select(Preset).where(Preset.name == "Default")).first()
        if preset is None:
            preset = Preset(name="Default")
            session.add(preset)
            session.commit()
            session.refresh(preset)

        settings = session.exec(select(AppSettings)).first()
        if settings is None:
            settings = AppSettings(
                active_preset_id=preset.id,
                weather_latitude=45.5017,
                weather_longitude=-73.5673,
                weather_timezone="auto",
                slideshow_duration=30,
            )
            session.add(settings)
            session.commit()


def _extract_calendar_url(calendar: Any) -> str:
    """Extract a stable calendar URL from a caldav calendar object."""
    href = getattr(calendar, "url", None) or getattr(calendar, "href", None)
    return str(href or calendar)


def _extract_calendar_name(calendar: Any, url: str) -> str:
    """Extract a human-readable calendar name with robust fallbacks."""
    name = getattr(calendar, "name", None)
    if isinstance(name, str) and name.strip():
        return name.strip()

    tail = url.rstrip("/").split("/")[-1]
    return tail or "Unnamed calendar"


def _extract_calendar_guid(calendar: Any, url: str) -> str:
    """Extract a stable calendar identifier used by selector options."""
    guid = getattr(calendar, "id", None)
    if isinstance(guid, str) and guid.strip():
        return guid.strip()
    tail = url.rstrip("/").split("/")[-1]
    return tail or url


def _caldav_timeout() -> int:
    """Return effective CalDAV timeout for CLI discovery (max of connect/read timeouts)."""
    connect = int(os.getenv("CALDAV_CONNECT_TIMEOUT_SECONDS", "10"))
    read = int(os.getenv("CALDAV_READ_TIMEOUT_SECONDS", "30"))
    return max(connect, read)


def _caldav_max_retries() -> int:
    return int(os.getenv("CALDAV_MAX_RETRIES", "3"))


def _caldav_verify_ssl() -> bool:
    return os.getenv("CALDAV_VERIFY_SSL", "true").lower() in ("true", "1", "yes")


def _discover_remote_calendars(base_url: str, username: str, password: str) -> list[RemoteCalendar]:
    """Discover calendars from a CalDAV principal account.

    Applies the same timeout and retry settings used by the CalDAV adapter so
    CLI discovery commands fail fast instead of hanging indefinitely when the
    server is slow.
    """
    import time

    import caldav

    timeout = _caldav_timeout()
    verify_ssl = _caldav_verify_ssl()
    max_retries = max(1, _caldav_max_retries())
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            client = caldav.DAVClient(
                url=base_url,
                username=username,
                password=password,
                timeout=timeout,
                ssl_verify_cert=verify_ssl,
            )
            principal = client.principal()
            calendars = principal.calendars()
            discovered: list[RemoteCalendar] = []

            for calendar in calendars:
                calendar_url = _extract_calendar_url(calendar)
                discovered.append(
                    RemoteCalendar(
                        guid=_extract_calendar_guid(calendar, calendar_url),
                        name=_extract_calendar_name(calendar, calendar_url),
                        url=calendar_url,
                    )
                )

            return discovered
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries:
                wait = min(2 ** (attempt - 1), 8)
                console.print(
                    f"[yellow]CalDAV discovery attempt {attempt}/{max_retries} failed: {exc}. "
                    f"Retrying in {wait}s...[/yellow]"
                )
                time.sleep(wait)

    raise typer.Exit(code=1) from last_exc


def _require_exactly_one_selector(guid: str | None, index: int | None, name: str | None) -> None:
    """Ensure exactly one of guid/index/name is provided."""
    selected = sum(value is not None for value in (guid, index, name))
    if selected != 1:
        raise typer.BadParameter("Provide exactly one selector: --guid, --index, or --name.")


def _select_calendar(
    calendars: list[RemoteCalendar],
    guid: str | None,
    index: int | None,
    name: str | None,
) -> RemoteCalendar:
    """Resolve one remote calendar from guid/index/name selector input."""
    _require_exactly_one_selector(guid, index, name)

    if index is not None:
        if index < 1 or index > len(calendars):
            raise typer.BadParameter(f"--index must be between 1 and {len(calendars)}")
        return calendars[index - 1]

    if guid is not None:
        for calendar in calendars:
            if calendar.guid == guid:
                return calendar
        raise typer.BadParameter(f"No calendar found for --guid={guid}")

    assert name is not None
    lowered_name = name.lower()
    for calendar in calendars:
        if calendar.name.lower() == lowered_name:
            return calendar
    raise typer.BadParameter(f"No calendar found for --name={name}")


def _default_caldav_url() -> str:
    return os.getenv("CALDAV_URL", "")


def _default_caldav_username() -> str:
    return os.getenv("CALDAV_USERNAME", "")


def _default_caldav_password() -> str:
    return os.getenv("CALDAV_PASSWORD", "")


def _default_timezone() -> str:
    """Return timezone used for user-facing timestamps."""
    return os.getenv("DEFAULT_TIMEZONE", "UTC")


def _format_user_facing_datetime(value: datetime | None) -> str:
    """Format datetimes in the configured user timezone for display."""
    if value is None:
        return "-"

    tz_name = _default_timezone()
    target_tz: tzinfo
    try:
        target_tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        target_tz = UTC

    normalized = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return normalized.astimezone(target_tz).isoformat()


def _ensure_caldav_url(base_url: str) -> None:
    """Validate CalDAV URL input."""
    if not base_url:
        raise typer.BadParameter("Missing CalDAV URL. Set --url or CALDAV_URL.")


def _parse_start_date(value: str | None) -> date | None:
    """Parse optional YYYY-MM-DD date for alarm processing windows."""
    if value is None:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise typer.BadParameter("--start-date must be in YYYY-MM-DD format.") from exc


@db_app.command("init")
def db_init() -> None:
    """Initialize database tables and default rows."""
    with console.status("Initializing database..."):
        _initialize_database()
    console.print("[green]Database initialized.[/green]")


@db_app.command("migrate")
def db_migrate() -> None:
    """Apply Alembic migrations to head."""
    alembic_ini = _repo_root() / "alembic.ini"
    if not alembic_ini.exists():
        raise typer.BadParameter(f"alembic.ini not found at {alembic_ini}")

    cfg = Config(str(alembic_ini))
    with console.status("Applying Alembic migrations..."):
        command.upgrade(cfg, "head")
    console.print("[green]Migrations applied.[/green]")


@caldav_app.command("list")
def caldav_list(
    url: str = typer.Option(default_factory=_default_caldav_url, help="CalDAV server URL."),
    username: str = typer.Option(
        default_factory=_default_caldav_username,
        help="CalDAV username.",
    ),
    password: str = typer.Option(
        default_factory=_default_caldav_password,
        help="CalDAV password.",
        hide_input=True,
    ),
) -> None:
    """List available calendars from the configured CalDAV account."""
    _ensure_caldav_url(url)

    with console.status("Discovering CalDAV calendars..."):
        calendars = _discover_remote_calendars(url, username, password)

    if not calendars:
        console.print("[yellow]No calendars found.[/yellow]")
        raise typer.Exit(code=0)

    table = Table(title="CalDAV calendars")
    table.add_column("Index", justify="right")
    table.add_column("GUID")
    table.add_column("Name")
    table.add_column("URL")

    for idx, calendar in enumerate(calendars, start=1):
        table.add_row(str(idx), calendar.guid, calendar.name, calendar.url)

    console.print(table)


@caldav_app.command("add")
def caldav_add(
    guid: str | None = typer.Option(default=None, help="Calendar GUID from caldav list."),
    index: int | None = typer.Option(
        default=None, help="Calendar index from caldav list (1-based)."
    ),
    name: str | None = typer.Option(default=None, help="Calendar name from caldav list."),
    label: str | None = typer.Option(default=None, help="Override stored label."),
    color: str = typer.Option(default="#3182ce", help="Calendar color.", show_default=True),
    url: str = typer.Option(default_factory=_default_caldav_url, help="CalDAV server URL."),
    username: str = typer.Option(
        default_factory=_default_caldav_username,
        help="CalDAV username.",
    ),
    password: str = typer.Option(
        default_factory=_default_caldav_password,
        help="CalDAV password.",
        hide_input=True,
    ),
) -> None:
    """Add one remote CalDAV calendar as a local calendar source."""
    _ensure_caldav_url(url)

    with console.status("Discovering CalDAV calendars..."):
        calendars = _discover_remote_calendars(url, username, password)
    selected = _select_calendar(calendars, guid=guid, index=index, name=name)

    async def _add_selected_calendar() -> None:
        service = _build_calendar_service()
        ui_context = await service.get_calendars_for_ui()
        for source in ui_context.get("sources", []):
            if source.url == selected.url:
                console.print(
                    f"[yellow]Already configured:[/yellow] {source.label} -> {source.url}"
                )
                return

        source_label = label or selected.name
        created = await service.create_source(source_label, selected.url, color)
        console.print("[green]Calendar source created.[/green]")

        table = Table(title="Configured source")
        table.add_column("ID", justify="right")
        table.add_column("Label")
        table.add_column("URL")
        table.add_column("Color")
        table.add_row(str(created.id), created.label, created.url, created.color)
        console.print(table)

    asyncio.run(_add_selected_calendar())


@caldav_app.command("added")
def caldav_added() -> None:
    """List configured calendar sources stored in the local database."""

    async def _list_added() -> None:
        service = _build_calendar_service()
        ui_context = await service.get_calendars_for_ui()
        sources = list(ui_context.get("sources", []))

        if not sources:
            console.print("[yellow]No calendars configured in DB.[/yellow]")
            return

        table = Table(title="Configured calendars")
        table.add_column("ID", justify="right")
        table.add_column("Label")
        table.add_column("URL")
        table.add_column("Color")

        for source in sources:
            table.add_row(
                str(source.id),
                source.label,
                source.url,
                source.color,
            )

        console.print(table)

    asyncio.run(_list_added())


@caldav_app.command("remove")
def caldav_remove(
    source_id: int = typer.Argument(..., help="Database source ID to remove."),
) -> None:
    """Remove a configured calendar source from the local database."""

    async def _remove_source() -> None:
        service = _build_calendar_service()
        deleted = await service.delete_source(source_id)
        if not deleted:
            console.print(f"[yellow]No calendar found for ID {source_id}.[/yellow]")
            raise typer.Exit(code=1)

        console.print(f"[green]Removed calendar source:[/green] {source_id}")

    asyncio.run(_remove_source())


@caldav_app.command("sync")
def caldav_sync(
    guid: str | None = typer.Option(
        default=None, help="Optional GUID selector to sync a calendar."
    ),
    index: int | None = typer.Option(
        default=None, help="Optional index selector to sync a calendar."
    ),
    name: str | None = typer.Option(
        default=None, help="Optional name selector to sync a calendar."
    ),
    url: str = typer.Option(default_factory=_default_caldav_url, help="CalDAV server URL."),
    username: str = typer.Option(
        default_factory=_default_caldav_username,
        help="CalDAV username.",
    ),
    password: str = typer.Option(
        default_factory=_default_caldav_password,
        help="CalDAV password.",
        hide_input=True,
    ),
) -> None:
    """Sync configured calendar sources, optionally ensuring one selected calendar is configured."""

    async def _sync_sources() -> None:
        service = _build_calendar_service()

        selector_count = sum(value is not None for value in (guid, index, name))
        if selector_count > 0:
            _ensure_caldav_url(url)
            with console.status("Discovering CalDAV calendars..."):
                calendars = _discover_remote_calendars(url, username, password)
            selected = _select_calendar(calendars, guid=guid, index=index, name=name)

            ui_context = await service.get_calendars_for_ui()
            existing_urls = {source.url for source in ui_context.get("sources", [])}
            if selected.url not in existing_urls:
                await service.create_source(selected.name, selected.url, "#3182ce")
                console.print(f"[green]Added missing source for sync:[/green] {selected.name}")

        with console.status("Syncing calendar sources..."):
            await service.sync_calendars()

        statuses = await service.get_sync_status()
        table = Table(title="Calendar sync")
        table.add_column("Source ID", justify="right")
        table.add_column("Status")
        table.add_column("Events", justify="right")
        table.add_column("Last synced")
        table.add_column("Errors", justify="right")

        for row in statuses:
            last_synced = _format_user_facing_datetime(row.last_synced_at)
            table.add_row(
                str(row.calendar_source_id),
                row.sync_status,
                str(row.event_count),
                last_synced,
                str(row.error_count),
            )

        console.print(table)

    asyncio.run(_sync_sources())


@alarms_app.command("process")
def alarms_process(
    start_date: str | None = typer.Option(
        default=None,
        help="Start date for recurrence expansion (YYYY-MM-DD). Defaults to today UTC.",
    ),
    days: int = typer.Option(
        default=30,
        min=1,
        help="Number of days to process from start-date.",
    ),
) -> None:
    """Process events and alarms from calendar_elements into alarmevent over a date range."""

    async def _normalize() -> None:
        service = _build_calendar_service()
        parsed_start_date = _parse_start_date(start_date)
        with console.status("Normalizing alarm occurrences..."):
            count = await service.normalize_alarm_occurrences(
                start_date=parsed_start_date,
                days=days,
            )

        console.print(f"[green]Normalized alarm occurrences:[/green] {count}")

    asyncio.run(_normalize())


@alarms_app.command("list")
def alarms_list() -> None:
    """List alarm occurrences stored in alarmevent."""

    async def _list() -> None:
        service = _build_alarms_service()
        state = await service.get_debug_alarm_state()
        alarms = list(state.get("alarm_events", []))

        if not alarms:
            console.print("[yellow]No alarms found.[/yellow]")
            return

        table = Table(title="Alarm events")
        table.add_column("ID")
        table.add_column("Source ID", justify="right")
        table.add_column("Event UID")
        table.add_column("Trigger")
        table.add_column("Dismissed")

        for alarm in alarms:
            table.add_row(
                str(alarm.get("id", "")),
                str(alarm.get("calendar_source_id", "")),
                str(alarm.get("calendar_event_uid", "")),
                str(alarm.get("trigger_time", "")),
                str(alarm.get("dismissed_at") or "-"),
            )

        console.print(table)

    asyncio.run(_list())

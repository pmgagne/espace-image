"""Data contracts for calendar module."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CalendarSourceDTO:
    """Data transfer object for a calendar source."""

    id: int
    label: str
    url: str
    color: str
    default_alarm_for_all_events: bool


@dataclass(frozen=True)
class SyncStatusDTO:
    """Data transfer object for calendar sync status."""

    calendar_source_id: int
    last_synced_at: str
    next_sync_at: str
    sync_status: str
    error_message: str | None = None
    error_count: int = 0


@dataclass(frozen=True)
class CalendarsUIContextDTO:
    """Data transfer object for calendar UI context."""

    sources: list[CalendarSourceDTO]
    sync_statuses: dict[int, SyncStatusDTO | None]

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
    event_count: int = 0


@dataclass(frozen=True)
class CalendarSourceSyncReportDTO:
    """Per-source report emitted by one calendar sync run."""

    calendar_source_id: int
    calendar_source_url: str
    sync_succeeded: bool
    changed: bool | None
    is_caldav: bool


@dataclass(frozen=True)
class CalendarSyncReportDTO:
    """Aggregated report emitted by one calendar sync run."""

    source_reports: list[CalendarSourceSyncReportDTO]


@dataclass(frozen=True)
class GeneralSyncResultDTO:
    """Outcome of a general sync run (calendar sync + alarm normalization)."""

    calendar_sync_success: bool
    alarms_sync_success: bool
    alarms_skipped: bool
    alarms_skip_reason: str | None = None
    normalized_alarm_count: int = 0


@dataclass(frozen=True)
class CalendarsUIContextDTO:
    """Data transfer object for calendar UI context."""

    sources: list[CalendarSourceDTO]
    sync_statuses: dict[int, SyncStatusDTO | None]

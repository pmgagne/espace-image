"""Data contracts for alarms module."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class AlarmEventDTO:
    """Data transfer object for an alarm event."""

    id: UUID
    trigger_time: str  # ISO format
    dismissed_at: str | None = None
    calendar_source_id: int | None = None
    calendar_event_uid: str | None = None

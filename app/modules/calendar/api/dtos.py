"""Calendar module data transfer objects."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class CalendarEventData:
    """DTO for calendar event."""

    uid: str
    summary: str
    description: str
    location: str
    event_start: datetime
    event_end: datetime
    event_tz: str | None
    all_day: bool
    trigger_time: datetime | None
    optional_trigger: bool


@dataclass
class SyncStatusData:
    """DTO for calendar sync status."""

    calendar_source_id: int
    last_synced_at: datetime | None
    sync_status: str
    error_message: str
    error_count: int

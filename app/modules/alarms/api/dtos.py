"""Alarms module data transfer objects."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class AlarmData:
    """DTO for alarm display."""

    uid: str
    name: str
    start: datetime
    end: datetime
    all_day: bool
    trigger_time: datetime
    tzid: str | None = None


@dataclass
class AlarmEventData:
    """DTO for alarm event record."""

    id: str
    trigger_time: datetime
    calendar_source_id: int | None
    calendar_event_uid: str | None
    dismissed_at: datetime | None = None

"""Transport-agnostic DTOs for calendar module."""

from .contracts import (
    CalendarSourceDTO,
    CalendarSourceSyncReportDTO,
    CalendarsUIContextDTO,
    CalendarSyncReportDTO,
    GeneralSyncResultDTO,
    SyncStatusDTO,
)
from .dtos import CalendarEventData, SyncStatusData

__all__ = [
    "CalendarEventData",
    "CalendarSourceDTO",
    "CalendarSourceSyncReportDTO",
    "CalendarSyncReportDTO",
    "CalendarsUIContextDTO",
    "GeneralSyncResultDTO",
    "SyncStatusDTO",
    "SyncStatusData",
]

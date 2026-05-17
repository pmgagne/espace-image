"""Sync gateway port for calendar module external ICS operations."""

from datetime import date
from typing import Protocol

from sqlmodel import Session

from app.modules.calendar.api.contracts import CalendarSyncReportDTO


class ICalendarSyncGateway(Protocol):
    """Infrastructure gateway for calendar synchronization and ICS fetches."""

    async def sync_calendar_events(self, session: Session) -> None:
        """Sync all configured calendar events using the given session."""
        ...

    async def sync_calendar_events_with_report(
        self, session: Session, force: bool = False
    ) -> CalendarSyncReportDTO:
        """Sync calendar events and return a per-source report for orchestration decisions.

        Args:
            force: When True, force a full resync for all sources even if CalDAV
                indicates no changes.
        """
        ...

    async def normalize_alarm_occurrences(
        self,
        session: Session,
        start_date: date | None = None,
        days: int = 30,
    ) -> int:
        """Normalize recurring occurrences and alarm triggers from calendar elements."""
        ...

    async def fetch_ics(self, url: str) -> str | None:
        """Fetch ICS content for a source URL."""
        ...

    async def mark_general_sync_completed(self, session: Session, source_ids: list[int]) -> None:
        """Persist completion timestamp for one general sync run across source statuses."""
        ...

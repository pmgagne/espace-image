"""Sync gateway port for calendar module external ICS operations."""

from datetime import date
from typing import Protocol

from sqlmodel import Session


class ICalendarSyncGateway(Protocol):
    """Infrastructure gateway for calendar synchronization and ICS fetches."""

    async def sync_calendar_events(self, session: Session) -> None:
        """Sync all configured calendar events using the given session."""
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

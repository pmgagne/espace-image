"""Calendar module public interface."""

from typing import Any, Protocol

from sqlmodel import Session


class ICalendarService(Protocol):
    """Public interface for calendar operations."""

    async def sync_calendars(self, session: Session) -> None:
        """Sync all configured calendar sources."""
        ...

    async def get_calendar_events_in_window(
        self,
        session: Session,
        days_back: int = 7,
        days_ahead: int = 7,
    ) -> list[dict[str, Any]]:
        """
        Fetch calendar events within a time window.

        Args:
            session: Database session.
            days_back: Number of days to look back.
            days_ahead: Number of days to look ahead.

        Returns:
            List of event dictionaries.
        """
        ...

    async def fetch_ics(self, url: str) -> str | None:
        """
        Fetch ICS content from URL with retry logic.

        Args:
            url: URL to fetch ICS from.

        Returns:
            ICS content string or None if fetch failed.
        """
        ...


def get_calendar_service() -> ICalendarService:
    """Dependency injection token for calendar service."""
    raise NotImplementedError("Calendar service not initialized")

"""Calendar module public interface."""

from typing import Any, Protocol

from sqlmodel import Session

from app.db.models import CalendarSource


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

    async def create_source(
        self, session: Session, label: str, url: str, color: str
    ) -> CalendarSource:
        """
        Create a new calendar source.

        Args:
            session: Database session.
            label: Display label for the calendar.
            url: WebCal or ICS URL.
            color: Hex color code (e.g., "#3182ce").

        Returns:
            Created CalendarSource.
        """
        ...

    async def update_source_defaults(
        self, session: Session, source_id: int, default_alarm: bool
    ) -> CalendarSource:
        """
        Update calendar source default alarm setting.

        Args:
            session: Database session.
            source_id: Calendar source ID.
            default_alarm: Whether to add default alarms for events.

        Returns:
            Updated CalendarSource.
        """
        ...

    async def delete_source(self, session: Session, source_id: int) -> bool:
        """
        Delete a calendar source.

        Args:
            session: Database session.
            source_id: Calendar source ID.

        Returns:
            True if source was deleted, False if not found.
        """
        ...

    async def get_sync_status(self, session: Session) -> list[dict[str, Any]]:  # noqa: ARG002
        """
        Get synchronization status for all calendar sources.

        Args:
            session: Database session.

        Returns:
            List of sync status dictionaries.
        """
        ...

        async def get_calendars_for_ui(self, session: Session) -> dict[str, Any]:
            """
            Get calendar sources and their sync status formatted for UI rendering.

            Args:
                session: Database session.

            Returns:
                Dictionary with 'sources' and 'sync_statuses' for template rendering.
            """
            ...

    async def get_debug_calendar_state(self, session: Session) -> dict[str, Any]:
        """
        Get calendar sources and sync status for debugging.

        Args:
            session: Database session.

        Returns:
            Dictionary with 'sources' and 'statuses' keys.
        """
        ...


def get_calendar_service() -> ICalendarService:
    """Dependency injection token for calendar service."""
    raise NotImplementedError("Calendar service not initialized")

"""Calendar module public interface."""

from datetime import date
from typing import Any, Protocol

from app.modules.calendar.api.contracts import CalendarSourceDTO, SyncStatusDTO


class ICalendarService(Protocol):
    """Public interface for calendar operations."""

    async def sync_calendars(self) -> None:
        """Sync all configured calendar sources."""
        ...

    async def normalize_alarm_occurrences(
        self,
        start_date: date | None = None,
        days: int = 30,
    ) -> int:
        """Build normalized alarm occurrences from stored calendar elements."""
        ...

    async def get_calendar_events_in_window(
        self,
        days_back: int = 7,
        days_ahead: int = 7,
    ) -> list[dict[str, Any]]:
        """
        Fetch calendar events within a time window.

        Args:
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

    async def create_source(self, label: str, url: str, color: str) -> CalendarSourceDTO:
        """
        Create a new calendar source.

        Args:
            label: Display label for the calendar.
            url: WebCal or ICS URL.
            color: Hex color code (e.g., "#3182ce").

        Returns:
            Created CalendarSource.
        """
        ...

    async def update_source_defaults(
        self, source_id: int, default_alarm: bool
    ) -> CalendarSourceDTO:
        """
        Update calendar source default alarm setting.

        Args:
            source_id: Calendar source ID.
            default_alarm: Whether to add default alarms for events.

        Returns:
            Updated CalendarSource.
        """
        ...

    async def delete_source(self, source_id: int) -> bool:
        """
        Delete a calendar source.

        Args:
            source_id: Calendar source ID.

        Returns:
            True if source was deleted, False if not found.
        """
        ...

    async def get_sync_status(self) -> list[SyncStatusDTO]:
        """
        Get synchronization status for all calendar sources.

        Args:
        Returns:
            List of sync status dictionaries.
        """
        ...

    async def get_latest_sync_utc_iso(self) -> str:
        """Return latest successful sync timestamp as an ISO string for UI polling."""
        ...

    async def get_calendars_for_ui(self) -> dict[str, Any]:
        """Get calendar sources and sync status formatted for UI rendering."""
        ...

    async def get_debug_calendar_state(self) -> dict[str, Any]:
        """
        Get calendar sources and sync status for debugging.

        Args:
        Returns:
            Dictionary with 'sources' and 'statuses' keys.
        """
        ...


def get_calendar_service() -> ICalendarService:
    """Dependency injection token for calendar service."""
    raise NotImplementedError("Calendar service not initialized")

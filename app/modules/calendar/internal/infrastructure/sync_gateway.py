"""Calendar sync gateway adapter wrapping legacy infrastructure service."""

from sqlmodel import Session

from app.modules.calendar.api.sync_gateway import ICalendarSyncGateway
from app.modules.calendar.internal.infrastructure.calendar_sync import (
    CalendarService as LegacyCalendarService,
)


class CalendarSyncGateway(ICalendarSyncGateway):
    """Adapter for ICS fetching and sync orchestration."""

    async def sync_calendar_events(self, session: Session) -> None:
        """Sync all configured calendar events using the given session."""
        await LegacyCalendarService.sync_calendar_events(session)

    async def fetch_ics(self, url: str) -> str | None:
        """Fetch ICS content for a source URL."""
        return await LegacyCalendarService.fetch_ics(url)

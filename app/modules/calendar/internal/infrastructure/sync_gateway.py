"""Calendar sync gateway implementing `ICalendarSyncGateway`.

Delegates calendar sync orchestration and ICS fetching to the
`CalendarService` implementation used by the module.
"""

from sqlmodel import Session

from app.modules.calendar.api.sync_gateway import ICalendarSyncGateway
from app.modules.calendar.internal.infrastructure.alarm_normalizer import (
    CalendarAlarmNormalizer,
)
from app.modules.calendar.internal.infrastructure.calendar_sync import (
    CalendarService,
)


class CalendarSyncGateway(ICalendarSyncGateway):
    """Adapter for ICS fetching and sync orchestration."""

    async def sync_calendar_events(self, session: Session) -> None:
        """Sync all configured calendar events using the given session."""
        await CalendarService.sync_calendar_events(session)

    async def normalize_alarm_occurrences(self, session: Session) -> int:
        """Normalize recurring occurrences and alarm triggers from calendar elements."""
        return await CalendarAlarmNormalizer.normalize(session)

    async def fetch_ics(self, url: str) -> str | None:
        """Fetch ICS content for a source URL."""
        return await CalendarService.fetch_ics(url)

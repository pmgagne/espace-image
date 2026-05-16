"""Calendar sync gateway implementing `ICalendarSyncGateway`.

Delegates calendar sync orchestration and ICS fetching to the
`CalendarService` implementation used by the module.
"""

from datetime import date

from sqlmodel import Session

from app.modules.calendar.api.contracts import CalendarSyncReportDTO
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

    async def sync_calendar_events_with_report(self, session: Session) -> CalendarSyncReportDTO:
        """Sync calendar events and return per-source metadata for orchestration."""
        return await CalendarService.sync_calendar_events_with_report(session)

    async def normalize_alarm_occurrences(
        self,
        session: Session,
        start_date: date | None = None,
        days: int = 30,
    ) -> int:
        """Normalize recurring occurrences and alarm triggers from calendar elements."""
        return await CalendarAlarmNormalizer.normalize(
            session,
            start_date=start_date,
            days=days,
        )

    async def fetch_ics(self, url: str) -> str | None:
        """Fetch ICS content for a source URL."""
        return await CalendarService.fetch_ics(url)

    async def mark_general_sync_completed(self, session: Session, source_ids: list[int]) -> None:
        """Persist completion timestamp for one general sync run."""
        CalendarService.mark_general_sync_completed(session, source_ids)

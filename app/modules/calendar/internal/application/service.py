"""Calendar service - wraps existing calendar logic and exposes module API."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from app.db.models import CalendarEventCache
from app.modules.calendar.internal.infrastructure.calendar_sync import (
    CalendarService as OriginalCalendarService,
)

logger = logging.getLogger(__name__)


class CalendarService:
    """Calendar service for sync, fetch, and event management."""

    async def sync_calendars(self, session: Session) -> None:
        """Sync all configured calendar sources."""
        await OriginalCalendarService.sync_calendar_events(session)

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
        utc_now = datetime.now(UTC)
        window_start = utc_now - timedelta(days=days_back)
        window_end = utc_now + timedelta(days=days_ahead)

        events = session.exec(
            select(CalendarEventCache).where(
                (CalendarEventCache.event_start <= window_end)
                & (CalendarEventCache.event_end >= window_start)
            )
        ).all()

        result = []
        for event in events:
            result.append(
                {
                    "uid": event.uid,
                    "summary": event.summary,
                    "description": event.description,
                    "location": event.location,
                    "event_start": event.event_start,
                    "event_end": event.event_end,
                    "event_tz": event.event_tz,
                    "all_day": event.all_day,
                    "trigger_time": event.trigger_time,
                    "calendar_source_id": event.calendar_source_id,
                }
            )

        return result

    async def fetch_ics(self, url: str) -> str | None:
        """
        Fetch ICS content from URL with retry logic.

        Args:
            url: URL to fetch ICS from.

        Returns:
            ICS content string or None if fetch failed.
        """
        return await OriginalCalendarService.fetch_ics(url)


def create_calendar_service() -> CalendarService:
    """Factory that returns the calendar service implementation."""
    return CalendarService()

"""Calendar infrastructure layer - repository for DB access."""

import logging
from typing import Any, cast

from sqlmodel import select

from app.db.models import (
    CalendarEventCache,
    CalendarSource,
    CalendarSyncStatusEntry,
)

logger = logging.getLogger(__name__)


class CalendarRepository:
    """Repository for calendar-related database operations."""

    def __init__(self, session_provider):
        """Initialize with a session provider (callable that returns Session)."""
        self.session_provider = session_provider

    def get_all_sources(self) -> list[CalendarSource]:
        """Fetch all calendar sources."""
        with self.session_provider() as session:
            return session.exec(select(CalendarSource)).all()

    def get_source_by_id(self, source_id: int) -> CalendarSource | None:
        """Fetch a calendar source by ID."""
        with self.session_provider() as session:
            return session.get(CalendarSource, source_id)

    def get_cached_events_in_window(
        self,
        window_start: Any,
        window_end: Any,
    ) -> list[CalendarEventCache]:
        """Fetch cached events within a time window."""
        with self.session_provider() as session:
            return session.exec(
                select(CalendarEventCache).where(
                    (CalendarEventCache.event_start <= window_end)
                    & (CalendarEventCache.event_end >= window_start)
                )
            ).all()

    def get_sync_status(self, source_id: int) -> CalendarSyncStatusEntry | None:
        """Fetch sync status for a calendar source."""
        with self.session_provider() as session:
            return session.exec(
                select(CalendarSyncStatusEntry).where(
                    CalendarSyncStatusEntry.calendar_source_id == source_id
                )
            ).first()

    def clear_cache_for_source(self, source_id: int) -> None:
        """Clear cached events for a calendar source."""
        with self.session_provider() as session:
            existing = session.exec(
                select(CalendarEventCache).where(CalendarEventCache.calendar_source_id == source_id)
            ).all()
            for event in existing:
                session.delete(event)
            session.commit()

    def add_cache_entry(
        self,
        source_id: int,
        uid: str,
        event_start: Any,
        event_end: Any,
        summary: str,
        description: str = "",
        location: str = "",
        event_tz: str | None = None,
        all_day: bool = False,
        trigger_time: Any | None = None,
        optional_trigger: bool = False,
    ) -> None:
        """Add or update a cached event."""
        with self.session_provider() as session:
            existing = session.exec(
                select(CalendarEventCache).where(
                    (CalendarEventCache.calendar_source_id == source_id)
                    & (CalendarEventCache.uid == uid)
                )
            ).first()

            if existing:
                existing.event_start = cast(Any, event_start)
                existing.event_end = cast(Any, event_end)
                existing.summary = summary
                existing.description = description
                existing.location = location
                existing.event_tz = event_tz
                existing.all_day = all_day
                existing.trigger_time = trigger_time
                existing.optional_trigger = optional_trigger
                session.add(existing)
            else:
                cache_entry = CalendarEventCache(
                    calendar_source_id=source_id,
                    uid=uid,
                    event_start=cast(Any, event_start),
                    event_end=cast(Any, event_end),
                    summary=summary,
                    description=description,
                    location=location,
                    event_tz=event_tz,
                    all_day=all_day,
                    trigger_time=trigger_time,
                    optional_trigger=optional_trigger,
                )
                session.add(cache_entry)
            session.commit()

    def update_sync_status(
        self,
        source_id: int,
        sync_status: str,
        last_synced_at: Any | None = None,
        error_message: str = "",
        error_count: int = 0,
        last_error_at: Any | None = None,
    ) -> None:
        """Update sync status for a calendar source."""
        with self.session_provider() as session:
            status = session.exec(
                select(CalendarSyncStatusEntry).where(
                    CalendarSyncStatusEntry.calendar_source_id == source_id
                )
            ).first()

            if not status:
                status = CalendarSyncStatusEntry(calendar_source_id=source_id)

            status.sync_status = sync_status
            if last_synced_at is not None:
                status.last_synced_at = last_synced_at
            status.error_message = error_message
            status.error_count = error_count
            if last_error_at is not None:
                status.last_error_at = last_error_at

            session.add(status)
            session.commit()

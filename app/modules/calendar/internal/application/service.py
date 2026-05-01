"""Calendar service - wraps existing calendar logic and exposes module API."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from app.db.models import CalendarEventCache, CalendarSource, CalendarSyncStatusEntry
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

    async def create_source(
        self, session: Session, label: str, url: str, color: str
    ) -> CalendarSource:
        """Create a new calendar source."""
        source = CalendarSource(label=label, url=url, color=color)
        session.add(source)
        session.commit()
        session.refresh(source)
        return source

    async def update_source_defaults(
        self, session: Session, source_id: int, default_alarm: bool
    ) -> CalendarSource:
        """Update calendar source default alarm setting."""
        source = session.get(CalendarSource, source_id)
        if not source:
            msg = f"Calendar source {source_id} not found"
            raise ValueError(msg)
        source.default_alarm_for_all_events = default_alarm
        session.add(source)
        session.commit()
        session.refresh(source)
        return source

    async def delete_source(self, session: Session, source_id: int) -> bool:
        """Delete a calendar source."""
        source = session.get(CalendarSource, source_id)
        if not source:
            return False
        session.delete(source)
        session.commit()
        return True

    async def get_sync_status(self, session: Session) -> list[dict[str, Any]]:
        """Get synchronization status for all calendar sources."""
        statuses = session.exec(select(CalendarSyncStatusEntry)).all()
        result = []
        for status in statuses:
            result.append(
                {
                    "id": status.id,
                    "calendar_source_id": status.calendar_source_id,
                    "last_synced_at": status.last_synced_at,
                    "next_sync_at": status.next_sync_at,
                    "sync_status": status.sync_status.value,
                    "error_message": status.error_message,
                    "error_count": status.error_count,
                    "last_error_at": status.last_error_at,
                }
            )
        return result

    async def get_debug_calendar_state(self, session: Session) -> dict[str, Any]:
        """Get calendar sources and sync status for debugging."""
        from app.utils.timezone import ensure_utc_aware

        sources = session.exec(select(CalendarSource)).all()
        statuses = session.exec(select(CalendarSyncStatusEntry)).all()

        src_out = [
            {
                "id": s.id,
                "label": s.label,
                "url": s.url,
            }
            for s in sources
        ]

        status_out = []
        for st in statuses:
            try:
                last_iso = (
                    ensure_utc_aware(st.last_synced_at).isoformat() if st.last_synced_at else None
                )
            except Exception:
                last_iso = st.last_synced_at.isoformat() if st.last_synced_at else None
            try:
                next_iso = (
                    ensure_utc_aware(st.next_sync_at).isoformat() if st.next_sync_at else None
                )
            except Exception:
                next_iso = st.next_sync_at.isoformat() if st.next_sync_at else None
            status_out.append(
                {
                    "calendar_source_id": st.calendar_source_id,
                    "last_synced_at": last_iso,
                    "next_sync_at": next_iso,
                    "sync_status": st.sync_status.value,
                    "error_message": st.error_message,
                    "error_count": st.error_count,
                }
            )

        return {"sources": src_out, "statuses": status_out}

    async def get_calendars_for_ui(self, session: Session) -> dict[str, Any]:
        """Get calendar sources and sync status formatted for UI rendering."""
        from app.utils.timezone import ensure_utc_aware

        sources = session.exec(select(CalendarSource)).all()
        sync_statuses = {}

        for source in sources:
            if source.id:
                status = session.exec(
                    select(CalendarSyncStatusEntry).where(
                        CalendarSyncStatusEntry.calendar_source_id == source.id
                    )
                ).first()
                if status:
                    try:
                        last_synced = (
                            ensure_utc_aware(status.last_synced_at).isoformat()
                            if status.last_synced_at
                            else ""
                        )
                    except Exception:
                        last_synced = ""
                    try:
                        next_sync = (
                            ensure_utc_aware(status.next_sync_at).isoformat()
                            if status.next_sync_at
                            else ""
                        )
                    except Exception:
                        next_sync = ""
                    sync_statuses[source.id] = {
                        "calendar_source_id": status.calendar_source_id,
                        "last_synced_at": last_synced,
                        "next_sync_at": next_sync,
                        "sync_status": status.sync_status.value,
                        "error_message": status.error_message,
                        "error_count": status.error_count,
                    }
                else:
                    sync_statuses[source.id] = None

        return {"sources": sources, "sync_statuses": sync_statuses}


def create_calendar_service() -> CalendarService:
    """Factory that returns the calendar service implementation."""
    return CalendarService()

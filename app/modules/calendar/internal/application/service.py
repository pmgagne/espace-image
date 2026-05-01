"""Calendar service - wraps existing calendar logic and exposes module API."""

import logging
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from app.db.models import CalendarEventCache, CalendarSource, CalendarSyncStatusEntry
from app.db.session_factory import SessionFactory
from app.modules.calendar.api.contracts import CalendarSourceDTO, SyncStatusDTO
from app.modules.calendar.internal.infrastructure.calendar_sync import (
    CalendarService as OriginalCalendarService,
)

logger = logging.getLogger(__name__)


class CalendarService:
    """Calendar service for sync, fetch, and event management."""

    def __init__(self, session_factory: SessionFactory) -> None:
        """Initialize calendar service with session factory dependency."""
        self._session_factory = session_factory

    @contextmanager
    def _session_scope(self, session: Session | None = None):
        """Yield provided session or create a local DB session."""
        if session is not None:
            yield session
            return
        with self._session_factory.session_scope() as local_session:
            yield local_session

    @staticmethod
    def _source_to_dto(source: CalendarSource) -> CalendarSourceDTO:
        """Convert CalendarSource ORM to CalendarSourceDTO."""
        return CalendarSourceDTO(
            id=source.id,
            label=source.label,
            url=source.url,
            color=source.color or "#3182ce",
            default_alarm_for_all_events=source.default_alarm_for_all_events,
        )

    @staticmethod
    def _status_to_dto(status: CalendarSyncStatusEntry) -> SyncStatusDTO:
        """Convert CalendarSyncStatusEntry ORM to SyncStatusDTO."""
        return SyncStatusDTO(
            calendar_source_id=status.calendar_source_id,
            last_synced_at=status.last_synced_at or "",
            next_sync_at=status.next_sync_at or "",
            sync_status=status.sync_status.value,
            error_message=status.error_message,
            error_count=status.error_count,
        )

    async def sync_calendars(self, session: Session | None = None) -> None:
        """Sync all configured calendar sources."""
        with self._session_scope(session) as active_session:
            await OriginalCalendarService.sync_calendar_events(active_session)

    async def get_calendar_events_in_window(
        self,
        days_back: int = 7,
        days_ahead: int = 7,
        session: Session | None = None,
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
        with self._session_scope(session) as active_session:
            utc_now = datetime.now(UTC)
            window_start = utc_now - timedelta(days=days_back)
            window_end = utc_now + timedelta(days=days_ahead)

            events = active_session.exec(
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
        self,
        label: str,
        url: str,
        color: str,
        session: Session | None = None,
    ) -> CalendarSourceDTO:
        """Create a new calendar source."""
        with self._session_scope(session) as active_session:
            source = CalendarSource(label=label, url=url, color=color)
            active_session.add(source)
            active_session.commit()
            active_session.refresh(source)
            return self._source_to_dto(source)

    async def update_source_defaults(
        self,
        source_id: int,
        default_alarm: bool,
        session: Session | None = None,
    ) -> CalendarSourceDTO:
        """Update calendar source default alarm setting."""
        with self._session_scope(session) as active_session:
            source = active_session.get(CalendarSource, source_id)
            if not source:
                msg = f"Calendar source {source_id} not found"
                raise ValueError(msg)
            source.default_alarm_for_all_events = default_alarm
            active_session.add(source)
            active_session.commit()
            active_session.refresh(source)
            return self._source_to_dto(source)

    async def delete_source(self, source_id: int, session: Session | None = None) -> bool:
        """Delete a calendar source."""
        with self._session_scope(session) as active_session:
            source = active_session.get(CalendarSource, source_id)
            if not source:
                return False
            active_session.delete(source)
            active_session.commit()
            return True

    async def get_sync_status(self, session: Session | None = None) -> list[SyncStatusDTO]:
        """Get synchronization status for all calendar sources."""
        with self._session_scope(session) as active_session:
            statuses = active_session.exec(select(CalendarSyncStatusEntry)).all()
            return [self._status_to_dto(status) for status in statuses]

    async def get_debug_calendar_state(self, session: Session | None = None) -> dict[str, Any]:
        """Get calendar sources and sync status for debugging."""
        from app.utils.timezone import ensure_utc_aware

        with self._session_scope(session) as active_session:
            sources = active_session.exec(select(CalendarSource)).all()
            statuses = active_session.exec(select(CalendarSyncStatusEntry)).all()

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
                        ensure_utc_aware(st.last_synced_at).isoformat()
                        if st.last_synced_at
                        else None
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

    async def get_calendars_for_ui(self, session: Session | None = None) -> dict[str, Any]:
        """Get calendar sources and sync status formatted for UI rendering."""
        from app.utils.timezone import ensure_utc_aware

        with self._session_scope(session) as active_session:
            sources = active_session.exec(select(CalendarSource)).all()
            sync_statuses = {}

            for source in sources:
                if source.id:
                    status = active_session.exec(
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
                        sync_statuses[source.id] = SyncStatusDTO(
                            calendar_source_id=status.calendar_source_id,
                            last_synced_at=last_synced,
                            next_sync_at=next_sync,
                            sync_status=status.sync_status.value,
                            error_message=status.error_message,
                            error_count=status.error_count,
                        )
                    else:
                        sync_statuses[source.id] = None

            return {
                "sources": [self._source_to_dto(s) for s in sources],
                "sync_statuses": sync_statuses,
            }


def create_calendar_service(session_factory: SessionFactory) -> CalendarService:
    """Factory that returns the calendar service implementation."""
    return CalendarService(session_factory)

"""Calendar repository adapter for SQLModel persistence."""

from datetime import datetime

from sqlmodel import Session, select

from app.db.models import CalendarEventCache, CalendarSource, CalendarSyncStatusEntry
from app.modules.calendar.api.repositories import ICalendarRepository


class CalendarRepository(ICalendarRepository):
    """SQLModel-backed repository for calendar use cases."""

    def list_events_in_window(
        self,
        session: Session,
        window_start: datetime,
        window_end: datetime,
    ) -> list[CalendarEventCache]:
        """Return cached events intersecting the requested time window."""
        return session.exec(
            select(CalendarEventCache).where(
                (CalendarEventCache.event_start <= window_end)
                & (CalendarEventCache.event_end >= window_start)
            )
        ).all()

    def create_source(
        self,
        session: Session,
        label: str,
        url: str,
        color: str,
    ) -> CalendarSource:
        """Create and persist one calendar source."""
        source = CalendarSource(label=label, url=url, color=color)
        session.add(source)
        session.commit()
        session.refresh(source)
        return source

    def get_source(self, session: Session, source_id: int) -> CalendarSource | None:
        """Return one calendar source by identifier."""
        return session.get(CalendarSource, source_id)

    def save_source(self, session: Session, source: CalendarSource) -> CalendarSource:
        """Persist calendar source updates."""
        session.add(source)
        session.commit()
        session.refresh(source)
        return source

    def delete_source(self, session: Session, source: CalendarSource) -> None:
        """Delete one calendar source row."""
        session.delete(source)
        session.commit()

    def list_statuses(self, session: Session) -> list[CalendarSyncStatusEntry]:
        """Return all sync status rows."""
        return session.exec(select(CalendarSyncStatusEntry)).all()

    def list_sources(self, session: Session) -> list[CalendarSource]:
        """Return all calendar source rows."""
        return session.exec(select(CalendarSource)).all()

    def get_status_for_source(
        self,
        session: Session,
        source_id: int,
    ) -> CalendarSyncStatusEntry | None:
        """Return sync status for one source identifier."""
        return session.exec(
            select(CalendarSyncStatusEntry).where(
                CalendarSyncStatusEntry.calendar_source_id == source_id
            )
        ).first()

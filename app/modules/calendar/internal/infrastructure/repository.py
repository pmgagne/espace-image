"""Calendar repository adapter for SQLModel persistence."""

from datetime import datetime

from sqlmodel import Session, select

from app.db.models import CalendarElement, CalendarSource, CalendarSyncStatusEntry
from app.modules.calendar.api.repositories import ICalendarRepository


class CalendarRepository(ICalendarRepository):
    """SQLModel-backed repository for calendar use cases."""

    def list_events_in_window(
        self,
        session: Session,
        _window_start: datetime,
        _window_end: datetime,
    ) -> list[CalendarElement]:
        """Return raw calendar elements for the requested source window call."""
        return list(session.exec(select(CalendarElement)).all())

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
        return list(session.exec(select(CalendarSyncStatusEntry)).all())

    def count_events_for_source(self, session: Session, source_id: int) -> int:
        """Return the number of cached events for one source."""
        from sqlmodel import func

        result = session.exec(
            select(func.count()).select_from(CalendarElement).where(
                CalendarElement.calendar_source_id == source_id
            )
        ).one()
        return result or 0

    def list_sources(self, session: Session) -> list[CalendarSource]:
        """Return all calendar source rows."""
        return list(session.exec(select(CalendarSource)).all())

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

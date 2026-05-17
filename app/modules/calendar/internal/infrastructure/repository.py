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

    def cleanup_source(self, session: Session, source_id: int) -> tuple[int, int, int]:
        """Remove sync status, calendar elements, and alarm events for a source.

        Returns a tuple of deleted counts: (sync_status_count, calendar_elements_count, alarm_events_count).
        This function centralizes cleanup so future removals (like old events) can be added here.
        """
        from app.db.models import AlarmEvent, CalendarElement, CalendarSyncStatusEntry

        # Collect rows to delete so we can count them
        statuses = list(
            session.exec(
                select(CalendarSyncStatusEntry).where(
                    CalendarSyncStatusEntry.calendar_source_id == source_id
                )
            ).all()
        )
        elements = list(
            session.exec(
                select(CalendarElement).where(CalendarElement.calendar_source_id == source_id)
            ).all()
        )
        alarms = list(
            session.exec(select(AlarmEvent).where(AlarmEvent.calendar_source_id == source_id)).all()
        )

        for st in statuses:
            session.delete(st)
        for el in elements:
            session.delete(el)
        for al in alarms:
            session.delete(al)

        session.commit()

        # After cleaning the specific source, also run an orphan cleanup to
        # ensure no stray rows remain for deleted or missing sources.
        try:
            self.cleanup_orphans(session)
        except Exception:
            # Best-effort: do not fail the per-source cleanup if orphan cleanup fails.
            pass

        return (len(statuses), len(elements), len(alarms))

    def cleanup_orphans(self, session: Session) -> tuple[int, int, int]:
        """Remove rows not tied to any active CalendarSource.

        Returns tuple of deleted counts: (sync_status_count, calendar_elements_count, alarm_events_count).
        """
        from sqlmodel import select

        from app.db.models import (
            AlarmEvent,
            CalendarElement,
            CalendarSource,
            CalendarSyncStatusEntry,
        )

        active_sources = list(session.exec(select(CalendarSource.id)).all())
        # SQLModel may return a list of scalars or tuples depending on the query;
        # normalize to a set of ints.
        active_ids: set[int] = set()
        for row in active_sources:
            if isinstance(row, (tuple, list)) and len(row) > 0:
                active_ids.add(row[0])
            else:
                active_ids.add(row)

        statuses = list(
            session.exec(
                select(CalendarSyncStatusEntry).where(
                    (CalendarSyncStatusEntry.calendar_source_id.is_(None))
                    if not active_ids
                    else (~CalendarSyncStatusEntry.calendar_source_id.in_(list(active_ids)))
                )
            ).all()
        )
        elements = list(
            session.exec(
                select(CalendarElement).where(
                    (CalendarElement.calendar_source_id.is_(None))
                    if not active_ids
                    else (~CalendarElement.calendar_source_id.in_(list(active_ids)))
                )
            ).all()
        )
        alarms = list(
            session.exec(
                select(AlarmEvent).where(
                    (AlarmEvent.calendar_source_id.is_(None))
                    if not active_ids
                    else (~AlarmEvent.calendar_source_id.in_(list(active_ids)))
                )
            ).all()
        )

        for st in statuses:
            session.delete(st)
        for el in elements:
            session.delete(el)
        for al in alarms:
            session.delete(al)

        session.commit()

        return (len(statuses), len(elements), len(alarms))

    def list_statuses(self, session: Session) -> list[CalendarSyncStatusEntry]:
        """Return all sync status rows."""
        return list(session.exec(select(CalendarSyncStatusEntry)).all())

    def count_events_for_source(self, session: Session, source_id: int) -> int:
        """Return the number of cached events for one source."""
        from sqlmodel import func

        result = session.exec(
            select(func.count())
            .select_from(CalendarElement)
            .where(CalendarElement.calendar_source_id == source_id)
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

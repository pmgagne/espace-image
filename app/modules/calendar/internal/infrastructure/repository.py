"""Calendar repository adapter for SQLModel persistence."""

from datetime import datetime
from typing import Any, cast

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

        return (len(statuses), len(elements), len(alarms))

    def cleanup_orphans(self, session: Session) -> tuple[int, int, int]:
        """Remove rows not tied to any active CalendarSource.

        Returns tuple of deleted counts: (sync_status_count, calendar_elements_count, alarm_events_count).
        """
        from app.db.models import AlarmEvent

        active_sources = list(session.exec(select(CalendarSource.id)).all())
        # SQLModel may return a list of scalars or tuples depending on the query;
        # normalize to a set of ints.
        active_ids: set[int] = set()
        for row in active_sources:
            if isinstance(row, (tuple, list)) and len(row) > 0:
                active_ids.add(row[0])
            else:
                active_ids.add(row)

        # A row is orphaned when it has a (non-null) source id that does not
        # belong to any surviving CalendarSource. NULL is never orphaned here:
        # for AlarmEvent it marks a simulated alarm (intentionally source-less,
        # see list_ready_simulated_alarms), and the other two tables never have
        # a null source id at all. This must hold even when active_ids is
        # empty (e.g. the last calendar source was just deleted) — otherwise
        # every remaining row would be skipped as "not orphaned" instead of
        # correctly being swept, or simulated alarms would be wrongly deleted.
        def _is_orphan(col: Any) -> Any:
            if active_ids:
                return col.isnot(None) & ~col.in_(list(active_ids))
            return col.isnot(None)

        statuses = list(
            session.exec(
                select(CalendarSyncStatusEntry).where(
                    _is_orphan(cast(Any, CalendarSyncStatusEntry.calendar_source_id))
                )
            ).all()
        )
        elements = list(
            session.exec(
                select(CalendarElement).where(
                    _is_orphan(cast(Any, CalendarElement.calendar_source_id))
                )
            ).all()
        )
        alarms = list(
            session.exec(
                select(AlarmEvent).where(_is_orphan(cast(Any, AlarmEvent.calendar_source_id)))
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

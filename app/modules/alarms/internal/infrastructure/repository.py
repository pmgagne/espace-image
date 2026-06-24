"""Alarms infrastructure layer - repository for DB access."""

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlmodel import Session, select

from app.db.models import AlarmEvent, CalendarEvent, CalendarSource
from app.modules.alarms.api.repositories import IAlarmsRepository


class AlarmsRepository(IAlarmsRepository):
    """Repository adapter for alarm-related persistence operations."""

    def list_calendar_sources(self, session: Session) -> list[CalendarSource]:
        """Return all calendar sources."""
        return list(session.exec(select(CalendarSource)).all())

    def list_cached_events_in_window(
        self,
        session: Session,
        source_id: int,
        window_start: datetime,
        window_end: datetime,
    ) -> list[CalendarEvent]:
        """Return cached events in a time window for one source."""
        return list(
            session.exec(
                select(CalendarEvent).where(
                    (CalendarEvent.calendar_source_id == source_id)
                    & (CalendarEvent.event_start <= window_end)
                    & (CalendarEvent.event_end >= window_start)
                )
            ).all()
        )

    def get_alarm_by_calendar_uid(
        self,
        session: Session,
        source_id: int,
        event_uid: str,
    ) -> AlarmEvent | None:
        """Return alarm row by calendar source and event UID."""
        return session.exec(
            select(AlarmEvent).where(
                (AlarmEvent.calendar_source_id == source_id)
                & (AlarmEvent.calendar_event_uid == event_uid)
            )
        ).first()

    def get_alarm_by_uuid(self, session: Session, alarm_id: UUID) -> AlarmEvent | None:
        """Return alarm row by UUID."""
        return session.exec(select(AlarmEvent).where(AlarmEvent.id == alarm_id)).first()

    def get_cached_event_by_uid(
        self,
        session: Session,
        source_id: int,
        event_uid: str,
    ) -> CalendarEvent | None:
        """Return cached event by source and UID."""
        return session.exec(
            select(CalendarEvent).where(
                (CalendarEvent.calendar_source_id == source_id) & (CalendarEvent.uid == event_uid)
            )
        ).first()

    def add_alarm(self, session: Session, alarm: AlarmEvent) -> None:
        """Stage an alarm row for persistence in current transaction."""
        session.add(alarm)

    def list_ready_simulated_alarms(
        self,
        session: Session,
        now_naive: datetime,
    ) -> list[AlarmEvent]:
        """Return simulated alarms ready to fire and not dismissed."""
        cs_col = cast(Any, AlarmEvent.calendar_source_id)
        dismissed_col = cast(Any, AlarmEvent.dismissed_at)
        return list(
            session.exec(
                select(AlarmEvent).where(
                    (cs_col.is_(None))
                    & (AlarmEvent.trigger_time <= now_naive)
                    & (dismissed_col.is_(None))
                )
            ).all()
        )

    def list_dismissed_before(
        self,
        session: Session,
        purge_before: datetime,
    ) -> list[AlarmEvent]:
        """Return dismissed alarms older than a threshold."""
        dismissed_col = cast(Any, AlarmEvent.dismissed_at)
        return list(
            session.exec(
                select(AlarmEvent).where(
                    (dismissed_col.isnot(None)) & (dismissed_col < purge_before)
                )
            ).all()
        )

    def list_triggered_before(
        self,
        session: Session,
        cutoff: datetime,
    ) -> list[AlarmEvent]:
        """Return alarms whose trigger_time is older than a threshold.

        Includes both dismissed and active rows so stale past occurrences are
        purged regardless of dismissal state.
        """
        trigger_col = cast(Any, AlarmEvent.trigger_time)
        return list(
            session.exec(select(AlarmEvent).where(trigger_col < cutoff)).all()
        )

    def delete_alarm(self, session: Session, alarm: AlarmEvent) -> None:
        """Delete one alarm row in current transaction."""
        session.delete(alarm)

    def list_cached_events(self, session: Session) -> list[CalendarEvent]:
        """Return all cached events for debug view."""
        return list(session.exec(select(CalendarEvent)).all())

    def list_all_alarms(self, session: Session) -> list[AlarmEvent]:
        """Return all alarm rows for debug view."""
        return list(session.exec(select(AlarmEvent)).all())

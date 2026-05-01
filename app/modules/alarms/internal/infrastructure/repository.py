"""Alarms infrastructure layer - repository for DB access."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import and_
from sqlmodel import select

from app.db.models import AlarmEvent

logger = logging.getLogger(__name__)


class AlarmsRepository:
    """Repository for alarm-related database operations."""

    def __init__(self, session_provider):
        """Initialize with a session provider (callable that returns Session)."""
        self.session_provider = session_provider

    def get_alarm_by_composite_uid(
        self,
        calendar_source_id: int,
        calendar_event_uid: str,
    ) -> AlarmEvent | None:
        """Fetch an alarm by composite UID (source_id + event_uid)."""
        with self.session_provider() as session:
            return session.exec(
                select(AlarmEvent).where(
                    (AlarmEvent.calendar_source_id == calendar_source_id)
                    & (AlarmEvent.calendar_event_uid == calendar_event_uid)
                )
            ).first()

    def create_alarm(
        self,
        trigger_time: datetime,
        calendar_source_id: int | None = None,
        calendar_event_uid: str | None = None,
    ) -> AlarmEvent:
        """Create a new alarm event."""
        with self.session_provider() as session:
            alarm = AlarmEvent(
                trigger_time=trigger_time,
                calendar_source_id=calendar_source_id,
                calendar_event_uid=calendar_event_uid,
            )
            session.add(alarm)
            session.commit()
            session.refresh(alarm)
            return alarm

    def dismiss_alarm(
        self,
        calendar_source_id: int,
        calendar_event_uid: str,
    ) -> None:
        """Mark an alarm as dismissed."""
        with self.session_provider() as session:
            alarm = session.exec(
                select(AlarmEvent).where(
                    (AlarmEvent.calendar_source_id == calendar_source_id)
                    & (AlarmEvent.calendar_event_uid == calendar_event_uid)
                )
            ).first()

            if alarm:
                alarm.dismissed_at = datetime.now(UTC)
                session.add(alarm)
                session.commit()

    def get_test_alarms(self) -> list[AlarmEvent]:
        """Fetch test/simulated alarms (no calendar link)."""
        with self.session_provider() as session:
            now_naive = datetime.now(UTC).replace(tzinfo=None)
            return session.exec(
                select(AlarmEvent).where(
                    (AlarmEvent.calendar_source_id.is_(None))  # type: ignore[union-attr]
                    & (AlarmEvent.trigger_time <= now_naive)
                    & (AlarmEvent.dismissed_at.is_(None))  # type: ignore[union-attr]
                )
            ).all()

    def purge_old_dismissed_alarms(self, days_old: int = 30) -> int:
        """
        Delete dismissed alarms older than specified days.

        Returns:
            Number of alarms purged.
        """
        with self.session_provider() as session:
            now = datetime.now(UTC)
            purge_before = now - timedelta(days=days_old)
            dismissed_col = cast(Any, AlarmEvent.dismissed_at)
            dismissed_alarms = session.exec(
                select(AlarmEvent).where(
                    and_(
                        dismissed_col.isnot(None),
                        dismissed_col < purge_before,
                    )
                )
            ).all()

            count = len(dismissed_alarms)
            if count > 0:
                logger.info(
                    "Purging %d dismissed alarms older than %s",
                    count,
                    purge_before.isoformat(),
                )
                for alarm in dismissed_alarms:
                    session.delete(alarm)
                session.commit()

            return count

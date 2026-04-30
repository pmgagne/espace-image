"""Alarms service - wraps existing alarm logic and exposes module API."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from app.db.models import (
    AlarmEvent,
    CalendarEventCache,
    CalendarSource,
)
from app.utils.timezone import ensure_utc_aware

logger = logging.getLogger(__name__)


class AlarmsService:
    """Alarms service for alarm display, dismissal, and maintenance."""

    async def get_active_alarms(self, session: Session) -> list[dict[str, Any]]:
        """
        Fetch active alarms that should be displayed.

        Args:
            session: Database session.

        Returns:
            List of alarm dictionaries.
        """
        # Fetch calendar alarms
        alarms = await self._fetch_calendar_alarms(session)
        # Fetch test/simulated alarms
        alarms.extend(self._fetch_simulated_alarms(session))
        return alarms

    async def _fetch_calendar_alarms(self, session: Session) -> list[dict[str, Any]]:
        """Fetch alarms from cached calendar events and filter dismissed ones."""
        utc_now = datetime.now(UTC)
        window_start = utc_now - timedelta(days=7)
        window_end = utc_now + timedelta(days=7)

        sources = session.exec(select(CalendarSource)).all()
        active_alarms: list[dict] = []

        for source in sources:
            cached_events = session.exec(
                select(CalendarEventCache).where(
                    (CalendarEventCache.calendar_source_id == source.id)
                    & (CalendarEventCache.event_start <= window_end)
                    & (CalendarEventCache.event_end >= window_start)
                )
            ).all()

            for event in cached_events:
                # Determine effective trigger time (fallback to event_start)
                trigger = (
                    event.trigger_time
                    if hasattr(event, "trigger_time") and event.trigger_time is not None
                    else event.event_start
                )

                # Normalize trigger to UTC-aware for safe comparisons
                try:
                    trigger_aware = ensure_utc_aware(trigger) if trigger is not None else None
                except Exception:
                    if trigger is None:
                        continue
                    trigger_aware = (
                        trigger
                        if getattr(trigger, "tzinfo", None) is not None
                        else trigger.replace(tzinfo=UTC)
                    )

                # Only show alarms when their trigger_time has been reached
                if trigger_aware is None or trigger_aware > utc_now:
                    continue

                composite_uid = f"{event.calendar_source_id}:{event.uid}"

                # Check if alarm was dismissed
                dismissed = session.exec(
                    select(AlarmEvent).where(
                        AlarmEvent.calendar_source_id == event.calendar_source_id,
                        AlarmEvent.calendar_event_uid == event.uid,
                    )
                ).first()

                if not dismissed or dismissed.dismissed_at is None:
                    alarm = {
                        "uid": composite_uid,
                        "name": event.summary,
                        "start": event.event_start,
                        "end": event.event_end,
                        "tzid": getattr(event, "event_tz", None),
                        "all_day": getattr(event, "all_day", False)
                        or (
                            getattr(event, "event_start", None) is not None
                            and getattr(event, "event_end", None) is not None
                            and getattr(event, "event_start", None).hour == 0
                            and getattr(event, "event_start", None).minute == 0
                            and (event.event_end - event.event_start).days >= 1
                        ),
                        "trigger_time": trigger,
                    }
                    active_alarms.append(alarm)

        return active_alarms

    def _fetch_simulated_alarms(self, session: Session) -> list[dict[str, Any]]:
        """Fetch test/simulated alarms from database."""
        now_naive = datetime.now(UTC).replace(tzinfo=None)

        # Test alarms have no calendar link (NULL calendar_source_id)
        simulated_alarms = session.exec(
            select(AlarmEvent).where(
                (AlarmEvent.calendar_source_id.is_(None))  # type: ignore[union-attr]
                & (AlarmEvent.trigger_time <= now_naive)
                & (AlarmEvent.dismissed_at.is_(None))  # type: ignore[union-attr]
            )
        ).all()

        alarms = []
        for alarm_event in simulated_alarms:
            try:
                start_dt = ensure_utc_aware(alarm_event.trigger_time)
            except Exception:
                start_dt = alarm_event.trigger_time

            try:
                end_dt = ensure_utc_aware(alarm_event.trigger_time + timedelta(hours=1))
            except Exception:
                end_dt = alarm_event.trigger_time + timedelta(hours=1)

            alarm = {
                "uid": str(alarm_event.id),
                "name": "Simulated Event",
                "start": start_dt,
                "end": end_dt,
                "all_day": False,
                "trigger_time": alarm_event.trigger_time,
                "tzid": None,
            }
            alarms.append(alarm)

        return alarms

    async def dismiss_alarm(self, alarm_uid: str, session: Session) -> None:
        """
        Mark an alarm as dismissed.

        Args:
            alarm_uid: Composite UID of alarm (calendar_source_id:event_uid) or UUID.
            session: Database session.
        """
        from uuid import UUID

        try:
            # Try parsing as UUID first
            try:
                alarm_uuid = UUID(alarm_uid)
                # Direct UUID lookup
                alarm = session.exec(select(AlarmEvent).where(AlarmEvent.id == alarm_uuid)).first()
                if alarm:
                    alarm.dismissed_at = datetime.now(UTC)
                    session.add(alarm)
                    session.commit()
                return
            except ValueError:
                # Not a UUID - parse as composite format "source_id:event_uid"
                pass

            # Parse composite UID format: "source_id:event_uid"
            parts = alarm_uid.split(":", 1)
            if len(parts) != 2:
                logger.warning(f"Invalid composite UID format: {alarm_uid}")
                return

            source_id = int(parts[0])
            event_uid = parts[1]

            # Lookup by calendar relationship
            alarm = session.exec(
                select(AlarmEvent).where(
                    (AlarmEvent.calendar_source_id == source_id)
                    & (AlarmEvent.calendar_event_uid == event_uid)
                )
            ).first()

            if alarm:
                # Update existing alarm
                alarm.dismissed_at = datetime.now(UTC)
                session.add(alarm)
            else:
                # Create new alarm record for this dismissal
                trigger_time = datetime.now(UTC)

                # Try to find cached event for accurate trigger time
                try:
                    cached = session.exec(
                        select(CalendarEventCache).where(
                            (CalendarEventCache.calendar_source_id == source_id)
                            & (CalendarEventCache.uid == event_uid)
                        )
                    ).first()
                    if cached:
                        trigger_time = cached.event_start
                except Exception as e:
                    logger.exception(
                        "DB lookup error while finding cached event for calendar_source_id=%s, uid=%s: %s",
                        source_id,
                        event_uid,
                        e,
                    )

                alarm = AlarmEvent(
                    trigger_time=trigger_time,
                    dismissed_at=datetime.now(UTC),
                    calendar_source_id=source_id,
                    calendar_event_uid=event_uid,
                )
                session.add(alarm)

            session.commit()
        except Exception as e:
            logger.error(f"Error dismissing alarm {alarm_uid}: {e}")

    async def purge_old_dismissed_alarms(self, session: Session) -> None:
        """Purge dismissed alarms older than 30 days."""
        try:
            now = datetime.now(UTC)
            purge_before = now - timedelta(days=30)
            dismissed_col = AlarmEvent.dismissed_at  # type: ignore[assignment]
            dismissed_alarms = session.exec(
                select(AlarmEvent).where(
                    (dismissed_col.isnot(None)) & (dismissed_col < purge_before)
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
        except Exception as e:
            logger.error(f"Error purging old dismissed alarms: {e}")


def create_alarms_service() -> AlarmsService:
    """Factory that returns the alarms service implementation."""
    return AlarmsService()

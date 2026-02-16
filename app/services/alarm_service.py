#!/usr/bin/env python3
# ruff: noqa
import logging
from datetime import datetime, timedelta
from typing import Any, Protocol, cast

from sqlalchemy import and_
from sqlmodel import Session, select

from app.db.models import AlarmEvent
from app.utils.timezone import ensure_utc_aware


class EventLike(Protocol):
    """Structural typing for calendar event-like objects used by AlarmService.

    Attributes are intentionally minimal and reflect the fields accessed
    by the service: `event_start`, `event_end`, `summary`, and `uid`.
    """

    event_start: datetime
    event_end: datetime
    summary: str
    uid: str | None


logger = logging.getLogger(__name__)


class AlarmService:
    """
    Service for alarm-related operations.

    Includes purging old dismissed alarms and formatting
    alarm events for display.
    """

    @staticmethod
    def purge_old_dismissed_alarms(session: Session) -> None:
        """
        Delete dismissed alarms older than 30 days.

        Args:
            session: SQLModel session for database operations.
        """
        now = ensure_utc_aware(datetime.now())
        purge_before = now - timedelta(days=30)
        dismissed_col = cast(Any, AlarmEvent.dismissed_at)
        dismissed_alarms = session.exec(
            select(AlarmEvent).where(
                and_(
                    dismissed_col.isnot(None),
                    dismissed_col < purge_before,
                )
            )
        ).all()
        if dismissed_alarms:
            logger.info(
                "Purging %d dismissed alarms older than %s",
                len(dismissed_alarms),
                purge_before.isoformat(),
            )
            for alarm_event in dismissed_alarms:
                session.delete(alarm_event)
            session.commit()

    @staticmethod
    def format_alarm(
        event: EventLike,
        composite_uid: str,
        utc_now: datetime,
        alarm_offset: timedelta | None = None,
    ) -> dict[str, Any] | None:
        """
        Format calendar event for alarm display.

        Determines all-day events, normalizes timezone info, and
        determines visibility relative to `utc_now`.

        Args:
            event: Event with `event_start`, `event_end`, `summary`.
            composite_uid: Composite unique identifier for the alarm.
            utc_now: Current UTC time for visibility logic.

        Returns:
            dict | None: Alarm dict if visible, else None.
        """
        # All-day event detection: if start is at 00:00 and duration >= 1 day
        is_all_day = (
            event.event_start.hour == 0
            and event.event_start.minute == 0
            and (event.event_end - event.event_start).days >= 1
        )
        # Determine the display time: event start, or start-of-day
        # for all-day events
        if is_all_day:
            display_time = event.event_start.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            display_time = event.event_start

        # Compute the actual alarm trigger time
        if alarm_offset is not None:
            trigger_time = display_time - alarm_offset
        else:
            trigger_time = display_time

        # Normalize display_time and event_end to UTC-aware datetimes
        try:
            display_time = ensure_utc_aware(display_time)
        except TypeError:
            logger.warning("Invalid display_time type: %r", display_time)
            display_time = event.event_start

        try:
            event_end = ensure_utc_aware(event.event_end)
        except TypeError:
            logger.warning(
                "Invalid event_end type: %r",
                getattr(event, "event_end", None),
            )
            event_end = event.event_end
        logger.debug(
            "Formatting alarm uid=%s composite=%s display_time=%s all_day=%s",
            getattr(event, "uid", "?"),
            composite_uid,
            getattr(display_time, "isoformat", lambda: "?")(),
            is_all_day,
        )

        # Show the alarm once its display time has arrived and
        # keep it until dismissed.
        if display_time <= utc_now:
            try:
                start_val = ensure_utc_aware(event.event_start)
            except TypeError:
                logger.warning("Invalid event_start type: %r", event.event_start)
                start_val = event.event_start

            end_val = event_end
            return {
                "uid": composite_uid,
                "name": event.summary,
                "start": start_val,
                "end": end_val,
                "all_day": is_all_day,
                "trigger_time": ensure_utc_aware(trigger_time),
            }
        return None

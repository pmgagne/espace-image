import logging
from datetime import datetime, timedelta

from sqlmodel import select

from app.db.models import AlarmEvent
from app.utils.timezone import ensure_utc_aware

logger = logging.getLogger(__name__)


class AlarmService:
    """
    Service for alarm-related operations, including purging old dismissed alarms and formatting alarm events for display.
    """

    @staticmethod
    def purge_old_dismissed_alarms(session) -> None:
        """
        Delete dismissed alarms older than 30 days.

        Args:
            session: SQLModel session for database operations.
        """
        now = ensure_utc_aware(datetime.now())
        purge_before = now - timedelta(days=30)
        dismissed_alarms = session.exec(
            select(AlarmEvent).where(
                (AlarmEvent.dismissed_at.is_not(None)) & (AlarmEvent.dismissed_at < purge_before)
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
    def format_alarm(event, composite_uid: str, utc_now: datetime) -> dict | None:
        """
        Format calendar event for alarm display.

        Determines all-day events, normalizes timezone info, and determines visibility relative to utc_now.

        Args:
            event: An event object with event_start, event_end, summary attributes.
            composite_uid (str): Composite unique identifier for the alarm.
            utc_now (datetime): The current UTC time for visibility logic.

        Returns:
            dict | None: Alarm dictionary if visible, else None.
        """
        # All-day event detection: if start is at 00:00 and duration >= 1 day
        is_all_day = (
            event.event_start.hour == 0
            and event.event_start.minute == 0
            and (event.event_end - event.event_start).days >= 1
        )
        # Determine the display time: event start, or start-of-day for all-day events
        if is_all_day:
            display_time = event.event_start.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            display_time = event.event_start

        # Normalize display_time and event_end to UTC-aware datetimes
        try:
            display_time = ensure_utc_aware(display_time)
        except TypeError:
            logger.warning("Invalid display_time type: %r", display_time)
            display_time = event.event_start

        try:
            event_end = ensure_utc_aware(event.event_end)
        except TypeError:
            logger.warning("Invalid event_end type: %r", getattr(event, "event_end", None))
            event_end = event.event_end
        logger.debug(
            "Formatting alarm uid=%s composite=%s display_time=%s all_day=%s",
            getattr(event, "uid", "?"),
            composite_uid,
            getattr(display_time, "isoformat", lambda: "?")(),
            is_all_day,
        )

        # Show the alarm once its display time has arrived and keep it until dismissed.
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
            }
        return None

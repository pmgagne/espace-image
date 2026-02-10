import logging
from datetime import UTC, datetime, timedelta
from sqlmodel import select

from app.db.models import AlarmEvent, CalendarEventCache


logger = logging.getLogger(__name__)


class AlarmService:
    @staticmethod
    def purge_old_dismissed_alarms(session) -> None:
        """Delete dismissed alarms older than 30 days."""
        now = datetime.now()
        purge_before = now - timedelta(days=30)
        dismissed_alarms = session.exec(
            select(AlarmEvent).where(
                (AlarmEvent.dismissed_at.is_not(None)) & (AlarmEvent.dismissed_at < purge_before)
            )
        ).all()
        for alarm_event in dismissed_alarms:
            session.delete(alarm_event)
        if dismissed_alarms:
            session.commit()

    @staticmethod
    def format_alarm(event, composite_uid, utc_now):
        """Format calendar event for alarm display.

        Preserves the logic moved from the router to determine all-day events,
        normalize timezone info, and determine visibility relative to utc_now.
        """
        # All-day event detection: if start is at 00:00 and duration >= 1 day
        is_all_day = (
            event.event_start.hour == 0
            and event.event_start.minute == 0
            and (event.event_end - event.event_start).days >= 1
        )
        # Determine the display time: event start, or start-of-day for all-day events
        try:
            if is_all_day:
                display_time = event.event_start.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                display_time = event.event_start
        except Exception:
            display_time = event.event_start
        # Normalize display_time and event_end to UTC-aware datetimes
        try:
            if getattr(display_time, "tzinfo", None) is None:
                display_time = display_time.replace(tzinfo=UTC)
        except Exception:
            pass
        try:
            event_end = (
                event.event_end
                if getattr(event.event_end, "tzinfo", None) is not None
                else event.event_end.replace(tzinfo=UTC)
            )
        except Exception:
            event_end = event.event_end
        # Show the alarm once its display time has arrived and keep it until dismissed.
        if display_time <= utc_now:
            try:
                start_val = (
                    event.event_start
                    if getattr(event.event_start, "tzinfo", None) is not None
                    else event.event_start.replace(tzinfo=UTC)
                )
            except Exception:
                start_val = event.event_start
            try:
                end_val = event_end
            except Exception:
                end_val = event.event_end
            return {
                "uid": composite_uid,
                "name": event.summary,
                "start": start_val,
                "end": end_val,
                "all_day": is_all_day,
            }
        return None

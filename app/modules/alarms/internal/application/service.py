"""Alarms service - wraps existing alarm logic and exposes module API."""

import logging
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from app.db.models import (
    AlarmEvent,
    CalendarEventCache,
    CalendarSource,
)
from app.db.session_factory import SessionFactory
from app.modules.alarms.api.contracts import AlarmEventDTO
from app.utils.timezone import datetime_to_iso_with_tz, ensure_utc_aware

logger = logging.getLogger(__name__)


class AlarmsService:
    """Alarms service for alarm display, dismissal, and maintenance."""

    def __init__(self, session_factory: SessionFactory) -> None:
        """Initialize alarms service with session factory dependency."""
        self._session_factory = session_factory

    @contextmanager
    def _session_scope(self, session: Session | None = None):
        """Yield provided session or create a local DB session."""
        if session is not None:
            yield session
            return
        with self._session_factory.session_scope() as local_session:
            yield local_session

    @staticmethod
    def _alarm_to_dto(alarm: AlarmEvent) -> AlarmEventDTO:
        """Convert AlarmEvent ORM to AlarmEventDTO."""
        return AlarmEventDTO(
            id=alarm.id,
            trigger_time=ensure_utc_aware(alarm.trigger_time).isoformat()
            if alarm.trigger_time
            else "",
            dismissed_at=ensure_utc_aware(alarm.dismissed_at).isoformat()
            if alarm.dismissed_at
            else None,
            calendar_source_id=alarm.calendar_source_id,
            calendar_event_uid=alarm.calendar_event_uid,
        )

    async def get_active_alarms(self, session: Session | None = None) -> list[dict[str, Any]]:
        """
        Fetch active alarms that should be displayed.

        Args:
            session: Database session.

        Returns:
            List of alarm dictionaries.
        """
        with self._session_scope(session) as active_session:
            # Fetch calendar alarms
            alarms = await self._fetch_calendar_alarms(active_session)
            # Fetch test/simulated alarms
            alarms.extend(self._fetch_simulated_alarms(active_session))
            return alarms

    async def create_simulated_alarm(
        self,
        delay_seconds: int,
        session: Session | None = None,
    ) -> AlarmEventDTO:
        """Create a simulated alarm that appears after the specified delay."""
        from uuid import uuid4

        with self._session_scope(session) as active_session:
            trigger_time = datetime.now(UTC) + timedelta(seconds=delay_seconds)
            alarm = AlarmEvent(
                id=uuid4(),
                trigger_time=trigger_time,
            )
            active_session.add(alarm)
            active_session.commit()
            return self._alarm_to_dto(alarm)

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

    async def dismiss_alarm(self, alarm_uid: str, session: Session | None = None) -> None:
        """
        Mark an alarm as dismissed.

        Args:
            alarm_uid: Composite UID of alarm (calendar_source_id:event_uid) or UUID.
            session: Database session.
        """
        from uuid import UUID

        with self._session_scope(session) as active_session:
            try:
                # Try parsing as UUID first
                try:
                    alarm_uuid = UUID(alarm_uid)
                    # Direct UUID lookup
                    alarm = active_session.exec(
                        select(AlarmEvent).where(AlarmEvent.id == alarm_uuid)
                    ).first()
                    if alarm:
                        alarm.dismissed_at = datetime.now(UTC)
                        active_session.add(alarm)
                        active_session.commit()
                    return
                except ValueError:
                    # Not a UUID - parse as composite format "source_id:event_uid"
                    pass

                # Parse composite UID format: "source_id:event_uid"
                parts = alarm_uid.split(":", 1)
                if len(parts) != 2:
                    logger.warning("Invalid composite UID format: %s", alarm_uid)
                    return

                source_id = int(parts[0])
                event_uid = parts[1]

                # Lookup by calendar relationship
                alarm = active_session.exec(
                    select(AlarmEvent).where(
                        (AlarmEvent.calendar_source_id == source_id)
                        & (AlarmEvent.calendar_event_uid == event_uid)
                    )
                ).first()

                if alarm:
                    # Update existing alarm
                    alarm.dismissed_at = datetime.now(UTC)
                    active_session.add(alarm)
                else:
                    # Create new alarm record for this dismissal
                    trigger_time = datetime.now(UTC)

                    # Try to find cached event for accurate trigger time
                    try:
                        cached = active_session.exec(
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
                    active_session.add(alarm)

                active_session.commit()
            except Exception as e:
                logger.error("Error dismissing alarm %s: %s", alarm_uid, e)

    async def purge_old_dismissed_alarms(self, session: Session | None = None) -> None:
        """Purge dismissed alarms older than 30 days."""
        with self._session_scope(session) as active_session:
            try:
                now = datetime.now(UTC)
                purge_before = now - timedelta(days=30)
                dismissed_col = AlarmEvent.dismissed_at  # type: ignore[assignment]
                dismissed_alarms = active_session.exec(
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
                        active_session.delete(alarm)
                    active_session.commit()
            except Exception as e:
                logger.error("Error purging old dismissed alarms: %s", e)

    async def get_debug_alarm_state(self, session: Session | None = None) -> dict[str, Any]:
        """Get cached calendar events and alarm events for debugging."""
        from app.utils.timezone import ensure_utc_aware

        with self._session_scope(session) as active_session:
            cached = active_session.exec(select(CalendarEventCache)).all()
            alarms = active_session.exec(select(AlarmEvent)).all()

            events_out = []
            for ev in cached:
                try:
                    start_iso = (
                        ensure_utc_aware(ev.event_start).isoformat() if ev.event_start else None
                    )
                except Exception:
                    start_iso = ev.event_start.isoformat() if ev.event_start else None
                try:
                    end_iso = ensure_utc_aware(ev.event_end).isoformat() if ev.event_end else None
                except Exception:
                    end_iso = ev.event_end.isoformat() if ev.event_end else None
                events_out.append(
                    {
                        "calendar_source_id": ev.calendar_source_id,
                        "uid": ev.uid,
                        "start": start_iso,
                        "end": end_iso,
                        "summary": ev.summary,
                        "tzid": getattr(ev, "event_tz", None),
                    }
                )

            alarms_out = []
            for a in alarms:
                try:
                    trig_iso = (
                        ensure_utc_aware(a.trigger_time).isoformat() if a.trigger_time else None
                    )
                except Exception:
                    trig_iso = a.trigger_time.isoformat() if a.trigger_time else None
                try:
                    dismissed_iso = (
                        ensure_utc_aware(a.dismissed_at).isoformat() if a.dismissed_at else None
                    )
                except Exception:
                    dismissed_iso = a.dismissed_at.isoformat() if a.dismissed_at else None
                alarms_out.append(
                    {
                        "id": str(a.id),  # Convert UUID to string
                        "calendar_source_id": a.calendar_source_id,
                        "calendar_event_uid": a.calendar_event_uid,
                        "trigger_time": trig_iso,
                        "dismissed_at": dismissed_iso,
                    }
                )

            return {"cached_events": events_out, "alarm_events": alarms_out}

    async def get_alarm_contexts(
        self,
        mock: bool = False,
        tz_offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return alarms transformed into template-ready dictionaries."""
        if mock:
            now = ensure_utc_aware(datetime.now())
            dt1 = now.replace(hour=14, minute=0, second=0, microsecond=0)
            dt2 = now.replace(hour=16, minute=30, second=0, microsecond=0)
            active_alarms = [
                {
                    "uid": "mock-1",
                    "name": "Meeting with Client",
                    "start": dt1,
                    "end": dt1 + timedelta(hours=1),
                    "all_day": False,
                },
                {
                    "uid": "mock-2",
                    "name": "Dentist Appointment",
                    "start": dt2,
                    "end": dt2 + timedelta(hours=1),
                    "all_day": False,
                },
                {
                    "uid": "mock-3",
                    "name": "Journée pédagogique",
                    "start": now.replace(hour=0, minute=0, second=0, microsecond=0),
                    "end": (now + timedelta(days=1)).replace(
                        hour=0,
                        minute=0,
                        second=0,
                        microsecond=0,
                    ),
                    "all_day": True,
                },
            ]
        else:
            await self.purge_old_dismissed_alarms()
            active_alarms = await self.get_active_alarms()

        return self._alarms_to_context(active_alarms, mock=mock, tz_offset=tz_offset)

    async def get_alarm_html(
        self,
        mock: bool = False,
        tz_offset: int | None = None,
    ) -> str:
        """
        Get rendered HTML for alarm component.

        Returns empty string if no alarms, otherwise returns alarm list HTML.
        """
        from app.template_config import templates

        alarm_contexts = await self.get_alarm_contexts(mock=mock, tz_offset=tz_offset)
        if not alarm_contexts:
            return ""

        tpl = templates.env.get_template("partials/alarms.html")
        return tpl.render(alarms=alarm_contexts)

    def _isoformat_safe(self, dt_obj: object, tzid: str | None = None) -> str:
        """Return timezone-aware ISO string or empty string on conversion failure."""
        if not dt_obj or not hasattr(dt_obj, "isoformat"):
            return ""
        try:
            return datetime_to_iso_with_tz(ensure_utc_aware(dt_obj), tzid)
        except Exception:
            logger.debug("Failed to isoformat: %s", dt_obj)
            return ""

    def _format_fallback_datetime(
        self,
        dt_obj: object,
        end_obj: object,
        all_day_flag: bool,
        start_iso_str: str,
    ) -> str:
        """Format a human-readable fallback datetime (French locale labels)."""
        try:
            if not dt_obj:
                return ""
            now_local = datetime.now(UTC)
            start_dt = (
                dt_obj
                if getattr(dt_obj, "tzinfo", None) is not None
                else dt_obj.replace(tzinfo=UTC)
            )

            days = [
                "Dimanche",
                "Lundi",
                "Mardi",
                "Mercredi",
                "Jeudi",
                "Vendredi",
                "Samedi",
            ]
            idx = start_dt.weekday() + 1 if start_dt.weekday() < 6 else 0
            month_names = [
                "janvier",
                "février",
                "mars",
                "avril",
                "mai",
                "juin",
                "juillet",
                "août",
                "septembre",
                "octobre",
                "novembre",
                "décembre",
            ]
            month = month_names[start_dt.month - 1]
            day_num = start_dt.day
            year_part = "" if start_dt.year == now_local.year else f" {start_dt.year}"
            day_text = f"{days[idx]}, {day_num} {month}{year_part}"

            if all_day_flag:
                return day_text

            def pad(n: int) -> str:
                return str(n).zfill(2)

            t1 = f"{pad(start_dt.hour)}:{pad(start_dt.minute)}"
            if end_obj:
                end_dt = end_obj if end_obj.tzinfo is not None else end_obj.replace(tzinfo=UTC)
                t2 = f"{pad(end_dt.hour)}:{pad(end_dt.minute)}"
                time_text = f"{t1}-{t2}" if t1 != t2 else t1
            else:
                time_text = t1

            return f"{day_text} {time_text}"
        except Exception as e:
            logger.debug("Failed to format fallback datetime: %s", e)
            return start_iso_str or ""

    def _alarms_to_context(
        self,
        active_alarms: list[dict[str, Any]],
        mock: bool = False,
        tz_offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """Convert raw alarms into template context sorted by most recent start time."""
        if not active_alarms:
            return []

        min_dt = datetime.min.replace(tzinfo=UTC)

        def _sort_key(item: dict[str, Any]):
            dt = item.get("start")
            if not dt:
                return min_dt
            try:
                return ensure_utc_aware(dt)
            except Exception:
                try:
                    return dt.replace(tzinfo=UTC)
                except Exception:
                    return min_dt

        active_alarms.sort(key=_sort_key, reverse=True)
        tz_query = f"&tz_offset={tz_offset}" if tz_offset is not None else ""

        contexts: list[dict[str, Any]] = []
        for alarm in active_alarms:
            tzid = alarm.get("tzid")
            start_iso = self._isoformat_safe(alarm.get("start"), tzid)
            end_iso = self._isoformat_safe(alarm.get("end"), tzid)
            all_day = bool(alarm.get("all_day", False))

            fallback_text = self._format_fallback_datetime(
                alarm.get("start"),
                alarm.get("end"),
                all_day,
                start_iso,
            )

            contexts.append(
                {
                    "uid": alarm.get("uid"),
                    "name": alarm.get("name", ""),
                    "fallback_text": fallback_text,
                    "start_iso": start_iso,
                    "end_iso": end_iso,
                    "all_day": "true" if all_day else "false",
                    "mock": mock,
                    "tz_query": tz_query,
                }
            )

        return contexts


def create_alarms_service(session_factory: SessionFactory) -> AlarmsService:
    """Factory that returns the alarms service implementation."""
    return AlarmsService(session_factory)


def alarms_to_context(
    active_alarms: list[dict[str, Any]],
    session_factory: SessionFactory,
    mock: bool = False,
    tz_offset: int | None = None,
) -> list[dict[str, Any]]:
    """
    Module-level helper for tests.

    Converts raw alarms into template context sorted by most recent start time.

    Args:
        active_alarms: List of alarm dictionaries.
        mock: Whether to use mock mode.
        tz_offset: Timezone offset in minutes.
        session_factory: SessionFactory for DI.
    """
    service = create_alarms_service(session_factory)
    return service._alarms_to_context(active_alarms, mock=mock, tz_offset=tz_offset)

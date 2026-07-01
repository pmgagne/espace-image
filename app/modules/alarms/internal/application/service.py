"""Alarms service - wraps existing alarm logic and exposes module API.

This implementation returns DTOs and contexts; HTML rendering is the
responsibility of GUI adapters or routers.
"""

import logging
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlmodel import Session

from app.config import ALARM_RETENTION_DAYS
from app.db.models import AlarmEntryType, AlarmEvent
from app.db.session_factory import SessionFactory
from app.modules.alarms.api.contracts import AlarmEventDTO
from app.modules.alarms.api.repositories import IAlarmsRepository
from app.modules.alarms.internal.infrastructure.repository import AlarmsRepository
from app.utils.timezone import datetime_to_iso_with_tz, ensure_utc_aware

logger = logging.getLogger(__name__)


class AlarmsService:
    """Alarms service for alarm display, dismissal, and maintenance."""

    def __init__(
        self,
        session_factory: SessionFactory,
        repository: IAlarmsRepository,
    ) -> None:
        """Initialize alarms service with session and repository dependencies."""
        self._session_factory = session_factory
        self._repository = repository

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
            entry_type=str(alarm.entry_type),
        )

    @staticmethod
    def _parse_calendar_entry_uid(
        entry_uid: str | None,
    ) -> tuple[str | None, str | None, datetime | None, datetime | None]:
        """Return entry kind, base UID, occurrence start, and trigger from stored identifiers."""
        if not entry_uid:
            return (None, None, None, None)

        parts = entry_uid.split("|")
        if len(parts) < 2:
            return (None, None, None, None)

        occurrence_start = None
        trigger_time = None
        if len(parts) >= 3:
            try:
                occurrence_start = ensure_utc_aware(datetime.fromisoformat(parts[2]))
            except Exception:
                occurrence_start = None
        if len(parts) >= 4:
            try:
                trigger_time = ensure_utc_aware(datetime.fromisoformat(parts[3]))
            except Exception:
                trigger_time = None
        return (parts[0], parts[1], occurrence_start, trigger_time)

    @staticmethod
    def _extract_summary_from_raw_ics(raw_ics: str | None) -> str | None:
        """Return unfolded ICS SUMMARY text when present."""
        if not raw_ics:
            return None

        unfolded_lines: list[str] = []
        for line in raw_ics.splitlines():
            if line.startswith((" ", "\t")) and unfolded_lines:
                unfolded_lines[-1] += line[1:]
                continue
            unfolded_lines.append(line)

        for line in unfolded_lines:
            upper = line.upper()
            if not upper.startswith("SUMMARY"):
                continue
            _, _, value = line.partition(":")
            summary = value.strip()
            return summary or None

        return None

    def _resolve_calendar_alarm_metadata(
        self,
        session: Session,
        source_id: int,
        base_uid: str,
        occurrence_start: datetime | None = None,
    ) -> tuple[str, str | None, bool, datetime | None, datetime | None]:
        """Resolve display metadata for one calendar occurrence from cached raw elements."""
        cached_event = self._repository.get_cached_event_by_uid(session, source_id, base_uid)
        name = "Untitled event"
        tzid = None
        all_day = False
        start_value = None
        end_value = None

        if cached_event is None:
            return (name, tzid, all_day, start_value, end_value)

        name = (
            getattr(cached_event, "summary", None)
            or getattr(cached_event, "description", None)
            or self._extract_summary_from_raw_ics(getattr(cached_event, "raw_ics", None))
            or "Untitled event"
        )
        tzid = getattr(cached_event, "event_tz", None)
        all_day = bool(getattr(cached_event, "all_day", False))
        start_value = getattr(cached_event, "event_start", None)
        end_value = getattr(cached_event, "event_end", None)

        if occurrence_start is not None:
            start_value = occurrence_start
            if cached_event is not None:
                cached_start = getattr(cached_event, "event_start", None)
                cached_end = getattr(cached_event, "event_end", None)
                if cached_start is not None and cached_end is not None:
                    end_value = occurrence_start + (cached_end - cached_start)
        return (name, tzid, all_day, start_value, end_value)

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
                entry_type=AlarmEntryType.SIMULATED,
            )
            active_session.add(alarm)
            active_session.commit()
            return self._alarm_to_dto(alarm)

    async def _fetch_calendar_alarms(self, session: Session) -> list[dict[str, Any]]:
        """Fetch active calendar alarms (VALARM rows) and enrich with metadata."""
        utc_now = datetime.now(UTC)
        window_start = utc_now - timedelta(days=7)
        active_alarms: list[dict[str, Any]] = []

        for alarm_row in self._repository.list_all_alarms(session):
            if alarm_row.calendar_source_id is None:
                continue
            if alarm_row.dismissed_at is not None:
                continue

            try:
                trigger_aware = ensure_utc_aware(alarm_row.trigger_time)
            except Exception:
                continue

            entry_type = str(alarm_row.entry_type)
            if entry_type != AlarmEntryType.ALARM.value:
                continue

            if trigger_aware < window_start or trigger_aware > utc_now:
                continue

            _, base_uid, occurrence_start, _ = self._parse_calendar_entry_uid(
                alarm_row.calendar_event_uid
            )
            if not base_uid:
                continue

            start_value = trigger_aware
            end_value = trigger_aware + timedelta(hours=1)
            name, tzid, all_day, cached_start, cached_end = self._resolve_calendar_alarm_metadata(
                session,
                alarm_row.calendar_source_id,
                base_uid,
                occurrence_start=occurrence_start,
            )
            if cached_start is not None:
                start_value = cached_start
            if cached_end is not None:
                end_value = cached_end

            active_alarms.append(
                {
                    "uid": f"{alarm_row.calendar_source_id}:{alarm_row.calendar_event_uid}",
                    "name": name,
                    "start": start_value,
                    "end": end_value,
                    "tzid": tzid,
                    "all_day": all_day,
                    "trigger_time": trigger_aware,
                    "entry_type": entry_type,
                }
            )

        return active_alarms

    def _fetch_simulated_alarms(self, session: Session) -> list[dict[str, Any]]:
        """Fetch test/simulated alarms from database."""
        now_naive = datetime.now(UTC).replace(tzinfo=None)

        # Test alarms have no calendar link (NULL calendar_source_id)
        simulated_alarms = self._repository.list_ready_simulated_alarms(session, now_naive)

        alarms: list[dict[str, Any]] = []
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
                "entry_type": AlarmEntryType.SIMULATED.value,
            }
            alarms.append(alarm)

        return alarms

    @staticmethod
    def _local_day_window_utc(tz_offset: int | None) -> tuple[datetime, datetime]:
        """Return today's local-day window converted to UTC bounds."""
        offset_minutes = int(tz_offset) if tz_offset is not None else 0
        now_utc = datetime.now(UTC)
        now_local = now_utc - timedelta(minutes=offset_minutes)
        local_day_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        utc_day_start = local_day_start + timedelta(minutes=offset_minutes)
        utc_day_end = utc_day_start + timedelta(days=1)
        return (utc_day_start, utc_day_end)

    async def get_today_payload(  # noqa: C901
        self,
        tz_offset: int | None,
        session: Session | None = None,
    ) -> dict[str, Any]:
        """Return today's alarms and events payload for frontend scheduling."""
        day_start_utc, day_end_utc = self._local_day_window_utc(tz_offset)
        now_utc = datetime.now(UTC)
        overdue_window_start = now_utc - timedelta(days=7)

        with self._session_scope(session) as active_session:
            alarms_for_popup: list[dict[str, Any]] = []
            events_for_day: list[dict[str, Any]] = []

            for alarm_row in self._repository.list_all_alarms(active_session):
                try:
                    trigger_aware = ensure_utc_aware(alarm_row.trigger_time)
                except Exception:
                    continue

                # Simulated alarms are popup-only and never part of the event list.
                if alarm_row.calendar_source_id is None:
                    if alarm_row.dismissed_at is not None:
                        continue
                    if trigger_aware <= day_end_utc:
                        alarms_for_popup.append(
                            {
                                "uid": str(alarm_row.id),
                                "name": "Simulated Event",
                                "start": trigger_aware,
                                "end": trigger_aware + timedelta(hours=1),
                                "all_day": False,
                                "trigger_time": trigger_aware,
                                "tzid": None,
                                "entry_type": AlarmEntryType.SIMULATED.value,
                            }
                        )
                    continue

                if alarm_row.calendar_event_uid is None:
                    continue

                entry_type = str(alarm_row.entry_type)
                _, base_uid, occurrence_start, _ = self._parse_calendar_entry_uid(
                    alarm_row.calendar_event_uid
                )
                if not base_uid:
                    continue

                start_value = trigger_aware
                end_value = trigger_aware + timedelta(hours=1)
                name, tzid, all_day, cached_start, cached_end = (
                    self._resolve_calendar_alarm_metadata(
                        active_session,
                        alarm_row.calendar_source_id,
                        base_uid,
                        occurrence_start=occurrence_start,
                    )
                )
                if cached_start is not None:
                    start_value = cached_start
                if cached_end is not None:
                    end_value = cached_end

                if entry_type == AlarmEntryType.ALARM.value:
                    if alarm_row.dismissed_at is not None:
                        continue
                    if overdue_window_start <= trigger_aware <= day_end_utc:
                        alarms_for_popup.append(
                            {
                                "uid": f"{alarm_row.calendar_source_id}:{alarm_row.calendar_event_uid}",
                                "name": name,
                                "start": start_value,
                                "end": end_value,
                                "tzid": tzid,
                                "all_day": all_day,
                                "trigger_time": trigger_aware,
                                "entry_type": entry_type,
                            }
                        )
                    continue

                if (
                    entry_type == AlarmEntryType.EVENT.value
                    and day_start_utc <= trigger_aware < day_end_utc
                ):
                    events_for_day.append(
                        {
                            "uid": f"{alarm_row.calendar_source_id}:{alarm_row.calendar_event_uid}",
                            "name": name,
                            "start": start_value,
                            "end": end_value,
                            "tzid": tzid,
                            "all_day": all_day,
                            "trigger_time": trigger_aware,
                            "entry_type": entry_type,
                        }
                    )

            alarm_contexts = self._alarms_to_context(
                alarms_for_popup,
                mock=False,
                tz_offset=tz_offset,
            )
            event_contexts = self._alarms_to_context(
                events_for_day,
                mock=False,
                tz_offset=tz_offset,
            )
            return {
                "fetched_at_utc": now_utc.isoformat(),
                "day_start_utc": day_start_utc.isoformat(),
                "day_end_utc": day_end_utc.isoformat(),
                "alarms": alarm_contexts,
                "events": event_contexts,
            }

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
                    alarm = self._repository.get_alarm_by_uuid(active_session, alarm_uuid)
                    if alarm:
                        alarm.dismissed_at = datetime.now(UTC)
                        self._repository.add_alarm(active_session, alarm)
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
                alarm = self._repository.get_alarm_by_calendar_uid(
                    active_session,
                    source_id,
                    event_uid,
                )

                if alarm:
                    # Update existing alarm
                    alarm.dismissed_at = datetime.now(UTC)
                    self._repository.add_alarm(active_session, alarm)
                else:
                    # Create new alarm record for this dismissal
                    trigger_time = datetime.now(UTC)

                    # Try to find cached event for accurate trigger time
                    try:
                        cached = self._repository.get_cached_event_by_uid(
                            active_session,
                            source_id,
                            event_uid,
                        )
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
                        entry_type=(
                            AlarmEntryType.EVENT
                            if event_uid.startswith("event|")
                            else AlarmEntryType.ALARM
                        ),
                    )
                    self._repository.add_alarm(active_session, alarm)

                active_session.commit()
            except Exception as e:
                logger.error("Error dismissing alarm %s: %s", alarm_uid, e)

    async def purge_old_dismissed_alarms(self, session: Session | None = None) -> None:
        """Purge dismissed alarms older than the retention window."""
        with self._session_scope(session) as active_session:
            try:
                now = datetime.now(UTC)
                purge_before = now - timedelta(days=ALARM_RETENTION_DAYS)
                dismissed_alarms = self._repository.list_dismissed_before(
                    active_session,
                    purge_before,
                )

                count = len(dismissed_alarms)
                if count > 0:
                    logger.info(
                        "Purging %d dismissed alarms older than %s",
                        count,
                        purge_before.isoformat(),
                    )
                    for alarm in dismissed_alarms:
                        self._repository.delete_alarm(active_session, alarm)
                    active_session.commit()
            except Exception as e:
                logger.error("Error purging old dismissed alarms: %s", e)

    async def purge_old_alarms(
        self,
        retention_days: int = ALARM_RETENTION_DAYS,
        session: Session | None = None,
    ) -> int:
        """Purge past alarm/event rows whose trigger_time is older than retention.

        Removes both dismissed and active rows so stale occurrences do not
        accumulate in the AlarmEvent table. Active/future alarms are untouched.

        Returns:
            Number of alarm rows deleted.
        """
        with self._session_scope(session) as active_session:
            try:
                cutoff = datetime.now(UTC) - timedelta(days=retention_days)
                old_alarms = self._repository.list_triggered_before(active_session, cutoff)

                count = len(old_alarms)
                if count > 0:
                    logger.info(
                        "Purging %d alarm rows triggered before %s",
                        count,
                        cutoff.isoformat(),
                    )
                    for alarm in old_alarms:
                        self._repository.delete_alarm(active_session, alarm)
                    active_session.commit()
                return count
            except Exception as e:
                logger.error("Error purging old alarms: %s", e)
                return 0

    async def get_debug_alarm_state(self, session: Session | None = None) -> dict[str, Any]:
        """Get cached calendar events and alarm events for debugging."""
        from app.utils.timezone import ensure_utc_aware

        with self._session_scope(session) as active_session:
            cached = self._repository.list_cached_events(active_session)
            alarms = self._repository.list_all_alarms(active_session)

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
                        "entry_type": str(a.entry_type),
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
        tz_offset: int | None,
    ) -> str:
        """Format a human-readable fallback datetime (French locale labels)."""
        try:
            if not dt_obj:
                return ""
            offset_minutes = int(tz_offset) if tz_offset is not None else 0
            now_local = datetime.now(UTC) - timedelta(minutes=offset_minutes)
            start_dt = ensure_utc_aware(dt_obj) - timedelta(minutes=offset_minutes)

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
                end_dt = ensure_utc_aware(end_obj) - timedelta(minutes=offset_minutes)
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
                tz_offset,
            )

            contexts.append(
                {
                    "uid": alarm.get("uid"),
                    "name": alarm.get("name", ""),
                    "fallback_text": fallback_text,
                    "trigger_iso": self._isoformat_safe(alarm.get("trigger_time"), tzid),
                    "start_iso": start_iso,
                    "end_iso": end_iso,
                    "all_day": "true" if all_day else "false",
                    "entry_type": alarm.get("entry_type", AlarmEntryType.ALARM.value),
                    "mock": mock,
                    "tz_query": tz_query,
                    "tz_offset": tz_offset,
                }
            )

        return contexts


def create_alarms_service(
    session_factory: SessionFactory,
    repository: IAlarmsRepository | None = None,
) -> AlarmsService:
    """Factory that returns the alarms service implementation."""
    return AlarmsService(
        session_factory,
        repository or AlarmsRepository(),
    )


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

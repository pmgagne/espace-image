"""Normalize calendar element ICS payloads into alarm occurrences.

This module is intentionally independent from sync: sync stores raw elements,
while this normalizer expands recurrence and computes trigger times to populate
`alarmevent` rows.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from app.db.models import AlarmEntryType, AlarmEvent, CalendarElement, CalendarSource
from app.modules.calendar.internal.infrastructure.calendar_sync import CalendarService
from app.utils.timezone import normalize_datetime


class CalendarAlarmNormalizer:
    """Build alarm occurrences from raw calendar elements."""

    @staticmethod
    def _extract_trigger_time(event: Any, start_utc: datetime) -> datetime:
        """Return trigger time from VALARM when available, else event start."""
        raw_component = getattr(event, "raw", None)
        subcomponents = getattr(raw_component, "subcomponents", None)
        if not subcomponents:
            return start_utc

        for sub in subcomponents:
            if getattr(sub, "name", "").upper() != "VALARM":
                continue
            trigger = sub.get("TRIGGER")
            if trigger is None:
                continue
            trigger_value = getattr(trigger, "dt", trigger)
            if isinstance(trigger_value, datetime):
                normalized = normalize_datetime(trigger_value)
                if normalized is not None:
                    return normalized
            if isinstance(trigger_value, timedelta):
                return start_utc + trigger_value

        return start_utc

    @staticmethod
    def _extract_trigger_times(event: Any, start_utc: datetime) -> list[datetime]:
        """Return one normalized trigger datetime for each VALARM on the event."""
        raw_component = getattr(event, "raw", None)
        subcomponents = getattr(raw_component, "subcomponents", None)
        if not subcomponents:
            return []

        trigger_times: list[datetime] = []
        for sub in subcomponents:
            if getattr(sub, "name", "").upper() != "VALARM":
                continue

            trigger = sub.get("TRIGGER")
            if trigger is None:
                continue

            trigger_value = getattr(trigger, "dt", trigger)
            if isinstance(trigger_value, datetime):
                normalized = normalize_datetime(trigger_value)
                if normalized is not None:
                    trigger_times.append(normalized)
                continue

            if isinstance(trigger_value, timedelta):
                trigger_times.append(start_utc + trigger_value)

        return trigger_times

    @staticmethod
    def _window_bounds(
        start_date: date | None,
        days: int,
    ) -> tuple[datetime, datetime]:
        """Return recurrence expansion bounds for normalized occurrences."""
        effective_days = max(1, days)
        base_date = start_date or (datetime.now(UTC).date() - timedelta(days=1))
        start = datetime(base_date.year, base_date.month, base_date.day, tzinfo=UTC)
        end = start + timedelta(days=effective_days)
        return (start, end)

    @staticmethod
    async def normalize(
        session: Session,
        start_date: date | None = None,
        days: int = 30,
    ) -> int:
        """Rebuild calendar-linked `alarmevent` rows from `calendar_elements`."""

        def _run() -> int:
            window_start, window_end = CalendarAlarmNormalizer._window_bounds(start_date, days)
            source_by_id = {
                source.id: source
                for source in session.exec(select(CalendarSource)).all()
                if source.id
            }
            elements = session.exec(select(CalendarElement)).all()

            dismissed_map: dict[tuple[int, str], datetime] = {}
            existing_calendar_alarms = [
                alarm
                for alarm in session.exec(select(AlarmEvent)).all()
                if alarm.calendar_source_id is not None
            ]
            for alarm in existing_calendar_alarms:
                if (
                    alarm.dismissed_at is not None
                    and alarm.calendar_source_id is not None
                    and alarm.calendar_event_uid is not None
                ):
                    dismissed_map[(alarm.calendar_source_id, alarm.calendar_event_uid)] = (
                        alarm.dismissed_at
                    )
                session.delete(alarm)
            session.flush()

            inserted = 0
            seen: set[tuple[int, str]] = set()

            for element in elements:
                source_id = element.calendar_source_id
                source = source_by_id.get(source_id)
                fix_icloud = bool(source and "icloud.com" in source.url)
                events = CalendarService.parse_ics_events(
                    element.raw_ics,
                    window_start,
                    window_end,
                    fix_icloud=fix_icloud,
                )

                for event in events:
                    start_utc = normalize_datetime(getattr(event, "start", None))
                    if start_utc is None:
                        continue

                    base_uid = str(getattr(event, "uid", "") or element.uid).strip()
                    if not base_uid:
                        continue
                    occurrence_key = f"{base_uid}|{start_utc.isoformat()}"

                    event_uid = f"event|{occurrence_key}"
                    event_dedupe_key = (source_id, event_uid)
                    if event_dedupe_key not in seen:
                        seen.add(event_dedupe_key)
                        session.add(
                            AlarmEvent(
                                trigger_time=start_utc,
                                dismissed_at=dismissed_map.get(event_dedupe_key),
                                calendar_source_id=source_id,
                                calendar_event_uid=event_uid,
                                entry_type=AlarmEntryType.EVENT,
                            )
                        )
                        inserted += 1

                    trigger_times = CalendarAlarmNormalizer._extract_trigger_times(event, start_utc)
                    for trigger_time in trigger_times:
                        alarm_uid = f"alarm|{occurrence_key}|{trigger_time.isoformat()}"
                        alarm_dedupe_key = (source_id, alarm_uid)
                        if alarm_dedupe_key in seen:
                            continue
                        seen.add(alarm_dedupe_key)

                        dismissed_at = dismissed_map.get(alarm_dedupe_key)
                        session.add(
                            AlarmEvent(
                                trigger_time=trigger_time,
                                dismissed_at=dismissed_at,
                                calendar_source_id=source_id,
                                calendar_event_uid=alarm_uid,
                                entry_type=AlarmEntryType.ALARM,
                            )
                        )
                        inserted += 1

            session.commit()
            return inserted

        return await asyncio.to_thread(_run)

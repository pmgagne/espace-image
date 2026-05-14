"""Normalize calendar element ICS payloads into alarm occurrences.

This module is intentionally independent from sync: sync stores raw elements,
while this normalizer expands recurrence and computes trigger times to populate
`alarmevent` rows.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from app.db.models import AlarmEvent, CalendarElement, CalendarSource
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
    def _window_bounds() -> tuple[datetime, datetime]:
        """Return wide recurrence expansion bounds for normalized occurrences."""
        return (datetime(2000, 1, 1, tzinfo=UTC), datetime(2100, 1, 1, tzinfo=UTC))

    @staticmethod
    async def normalize(session: Session) -> int:
        """Rebuild calendar-linked `alarmevent` rows from `calendar_elements`."""

        def _run() -> int:
            window_start, window_end = CalendarAlarmNormalizer._window_bounds()
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
                    occurrence_uid = f"{base_uid}:{start_utc.isoformat()}"

                    dedupe_key = (source_id, occurrence_uid)
                    if dedupe_key in seen:
                        continue
                    seen.add(dedupe_key)

                    trigger_time = CalendarAlarmNormalizer._extract_trigger_time(event, start_utc)
                    dismissed_at = dismissed_map.get(dedupe_key)
                    session.add(
                        AlarmEvent(
                            trigger_time=trigger_time,
                            dismissed_at=dismissed_at,
                            calendar_source_id=source_id,
                            calendar_event_uid=occurrence_uid,
                        )
                    )
                    inserted += 1

            session.commit()
            return inserted

        return await asyncio.to_thread(_run)

#!/usr/bin/env python3
# ruff: noqa
import asyncio
import logging
import os
import random
from datetime import UTC, date, datetime, timedelta, tzinfo
from typing import Any, cast
from zoneinfo import ZoneInfo

import backoff
from icalevents.icaldownload import ICalDownload
from icalevents.icalevents import events as icalevents_events
from icalevents.icalparser import Event as ICalEvent
from sqlalchemy import and_
from sqlmodel import Session, select

from app.db.models import (
    AlarmEvent,
    CalendarEventCache,
    CalendarSource,
    CalendarSyncStatus,
    CalendarSyncStatusEntry,
)
from app.utils.timezone import ensure_utc_aware, normalize_datetime

logger = logging.getLogger(__name__)


class CalendarService:
    """
    Service for fetching, parsing, and caching calendar events from ICS feeds.

    Provides static and async methods to:
    - Download and parse iCalendar (ICS) feeds from configured sources
    - Cache and update calendar events
        - Extract alarms and event data for use in the dashboard
            and other consumers
    """

    @staticmethod
    def _get_local_tz() -> tzinfo | None:
        """
        Return the local timezone to use for naive datetimes.

        Prefers the `TZ` environment variable (ZoneInfo name). Falls back to
        the system local timezone if available.

        Returns:
            ZoneInfo | None: The detected local timezone, or None if
            unavailable.
        """
        tzname = os.environ.get("TZ")
        if tzname:
            try:
                return ZoneInfo(tzname)
            except Exception:
                logger.debug("Invalid TZ environment value: %s", tzname)
        # Last-resort: use system local tzinfo from an aware datetime
        try:
            return datetime.now().astimezone().tzinfo
        except Exception:
            return None

    @staticmethod
    def _on_backoff(details: Any) -> None:
        """
        Callback for backoff retry attempts.

        Args:
            details (dict): Details about the backoff attempt.
        """
        tries = details.get("tries", 0)
        exception = details.get("exception")
        wait = details.get("wait", 0)
        logger.info(
            f"Retrying calendar fetch (attempt {tries}/5): "
            f"Exception: {exception.__class__.__name__}, "
            f"waiting {wait:.1f}s"
        )

    @staticmethod
    def _on_giveup(details: Any) -> None:
        """
        Callback when backoff gives up after max retries.

        Args:
            details (dict): Details about the giveup event.
        """
        tries = details.get("tries", 0)
        exception = details.get("exception")
        logger.warning(
            f"Failed to fetch ICS after {tries} attempts: "
            f"{exception.__class__.__name__}: {exception}"
        )

    @staticmethod
    def parse_ics_events(
        ics_content: str,
        start: datetime,
        end: datetime,
        tzinfo: tzinfo | None = None,
        fix_icloud: bool = False,
    ) -> list[ICalEvent]:
        """
        Parse ICS content string into a list of ICalEvent objects.

        Uses the icalevents library for parsing and attaches raw icalendar
        component data to each event for VALARM access.

        Args:
            ics_content (str): The raw ICS data as a string.
            start (datetime): Start of the window for event extraction.
            end (datetime): End of the window for event extraction.
            tzinfo (ZoneInfo | None): Timezone to use for parsing, if any.
            fix_icloud (bool):
                Whether to apply iCloud/Apple-specific parsing
                workarounds.

        Returns:
            list[ICalEvent]: List of parsed calendar events with .raw attached.
        """
        # Parse with icalendar to get raw component data
        raw_events_by_uid: dict[str, Any] = {}
        try:
            from icalendar import Calendar

            cal = Calendar.from_ical(ics_content)
            for component in cal.walk():
                if component.name == "VEVENT":
                    uid = str(component.get("UID", ""))
                    if uid:
                        raw_events_by_uid[uid] = component
        except Exception as e:
            logger.debug(f"Failed to parse ICS with icalendar: {e}")

        base_kwargs: dict[str, Any] = {
            "string_content": ics_content,
            "start": start,
            "end": end,
            "tzinfo": tzinfo,
        }
        if fix_icloud:
            candidate_flags = ["fix_apple", "fix_icloud", "fix_apple_icloud"]
            events_fn = cast(Any, icalevents_events)
            for flag in candidate_flags:
                try:
                    kwargs = base_kwargs.copy()
                    kwargs[flag] = True
                    logger.debug(
                        "Trying icalevents parser with flag: %s",
                        flag,
                    )
                    events = events_fn(**kwargs)
                    # Attach raw components to icalevents Event objects
                    for event in events:
                        uid = str(getattr(event, "uid", ""))
                        if uid in raw_events_by_uid:
                            event.raw = raw_events_by_uid[uid]  # type: ignore[attr-defined]
                    return events
                except TypeError:
                    # Unexpected kwarg for this icalevents version; try next
                    continue
                except Exception as e:
                    logger.warning(
                        "icalevents failed with %s=True: %s",
                        flag,
                        e,
                    )
                    return []
        try:
            events_fn = cast(Any, icalevents_events)
            events = events_fn(**base_kwargs)
            # Attach raw components to icalevents Event objects
            for event in events:
                uid = str(getattr(event, "uid", ""))
                if uid in raw_events_by_uid:
                    event.raw = raw_events_by_uid[uid]  # type: ignore[attr-defined]
            return events
        except Exception as e:
            logger.warning("Failed to parse ICS content: %s", e)
            return []

    @staticmethod
    def _has_non_time_alarm(_component: object) -> bool:
        """
        Legacy: kept for compatibility.

        Use `_detect_proximity_uids` on raw ICS instead.

        Args:
            _component (object): Unused; kept for interface compatibility.

        Returns:
            bool: Always False in this implementation.
        """
        return False

    @staticmethod
    def _to_datetime(val: datetime | date | None) -> datetime | None:
        """
        Normalize a date or datetime to an aware UTC datetime using utilities.

        Args:
            val (datetime | date | None): The value to normalize.

        Returns:
            datetime: A UTC-aware datetime object.
        """
        return normalize_datetime(val)

    @staticmethod
    def _detect_proximity_uids(ics_content: str) -> set[str]:
        """
        Scan raw ICS content and return a set of UIDs for VEVENTs that contain
        a VALARM with a PROXIMITY property.
        This is a lightweight heuristic.
        It is string-based to preserve previous behavior.

        Args:
            ics_content (str): The raw ICS data as a string.

        Returns:
            set[str]: Set of UIDs for events with proximity alarms.
        """
        uids: set[str] = set()
        try:
            parts = ics_content.split("BEGIN:VEVENT")
            for part in parts[1:]:
                # Is there a VALARM with PROXIMITY in this VEVENT block?
                if "BEGIN:VALARM" in part and "PROXIMITY" in part:
                    # extract UID line
                    for line in part.splitlines():
                        if line.strip().upper().startswith("UID:"):
                            uid = line.split(":", 1)[1].strip()
                            uids.add(uid)
                            break
        except Exception:
            logger.debug("Failed to detect proximity VALARM from ICS content")
        return uids

    @staticmethod
    def _extract_trigger_from_raw(ics_content: str, uid: str) -> str | None:
        """
        Scan raw ICS content for a VEVENT with matching UID and return the
        first VALARM TRIGGER value (string) or the string 'PROXIMITY' if a
        proximity VALARM is present. Returns None if not found.
        """
        try:
            parts = ics_content.split("BEGIN:VEVENT")
            for part in parts[1:]:
                # match UID line
                uid_line = None
                for line in part.splitlines():
                    if line.strip().upper().startswith("UID:"):
                        uid_line = line.split(":", 1)[1].strip()
                        break
                if not uid_line or uid_line != uid:
                    continue
                # Found VEVENT block for this UID
                if "BEGIN:VALARM" in part:
                    # Find PROXIMITY first
                    if "PROXIMITY" in part:
                        return "PROXIMITY"
                    # Find TRIGGER line
                    for line in part.splitlines():
                        if line.strip().upper().startswith("TRIGGER:"):
                            return line.split(":", 1)[1].strip()
                return None
        except Exception:
            return None
        return None

    @staticmethod
    def get_upcoming_alarms(
        ics_content: str,
        check_time: datetime,
        lookahead_minutes: int = 0,
        lookback_minutes: int = 60 * 12,
        tzinfo: tzinfo | None = None,
        fix_icloud: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Returns a list of events starting within the next `lookahead_minutes`
        OR that started in the last `lookback_minutes` (e.g. today).

        Args:
            ics_content (str): The raw ICS data as a string.
            check_time (datetime): The reference time for alarm calculation.
            lookahead_minutes (int): Minutes ahead to include events.
            lookback_minutes (int): Minutes back to include events.
            tzinfo (ZoneInfo | None): Timezone to use for parsing, if any.
            fix_icloud (bool):
                Whether to apply iCloud/Apple-specific parsing
                workarounds.

        Returns:
            list[dict]: List of alarm event dictionaries.
        """
        alarms: list[dict[str, Any]] = []
        lower_bound = check_time - timedelta(minutes=lookback_minutes)
        upper_bound = check_time + timedelta(minutes=lookahead_minutes)
        events = CalendarService.parse_ics_events(
            ics_content,
            lower_bound,
            upper_bound,
            tzinfo=tzinfo,
            fix_icloud=fix_icloud,
        )
        local_tz = CalendarService._get_local_tz()

        def extract_trigger_time(event: ICalEvent) -> datetime | None:
            """
            Extract the alarm trigger time from event.raw.subcomponents (VALARM/TRIGGER).
            Returns the absolute UTC datetime when the alarm should fire, or None if not found.
            For proximity alarms (no TRIGGER), returns event start time.
            """
            try:
                # event.raw is a icalendar.Event; subcomponents are VALARM(s)
                if not hasattr(event, "raw") or not hasattr(event.raw, "subcomponents"):  # type: ignore[attr-defined]
                    return None
                event_start = event.start
                if event_start is None:
                    return None
                # If event_start is naive, use local_tz if available
                if event_start.tzinfo is None and local_tz is not None:
                    event_start = event_start.replace(tzinfo=local_tz)
                for sub in getattr(event.raw, "subcomponents", []):  # type: ignore[attr-defined]
                    if getattr(sub, "name", "").upper() == "VALARM":
                        trigger = sub.get("TRIGGER")
                        if trigger is None:
                            # Check for proximity alarm (PROXIMITY:ARRIVE/DEPART)
                            proximity = sub.get("PROXIMITY")
                            if proximity is not None:
                                logger.debug(
                                    "Proximity alarm detected (no TRIGGER): %s",
                                    getattr(event, "uid", "?"),
                                )
                                # Proximity alarms fire at event start time
                                return event_start.astimezone(UTC)
                            continue
                        # icalendar parses TRIGGER as vDDDTypes (timedelta or datetime)
                        # See: https://icalendar.readthedocs.io/en/latest/usage.html#alarms
                        # Relative: -PT10M (timedelta), Absolute: 20260215T120000Z (datetime)
                        if hasattr(trigger, "dt"):
                            # vDDDTypes object with .dt attribute
                            trig_val = trigger.dt
                            if isinstance(trig_val, datetime):
                                # Absolute datetime
                                if trig_val.tzinfo is None and local_tz is not None:
                                    trig_val = trig_val.replace(tzinfo=local_tz)
                                return trig_val.astimezone(UTC)
                            elif isinstance(trig_val, timedelta):
                                # Relative offset from event_start
                                return (event_start + trig_val).astimezone(UTC)
                        elif isinstance(trigger, timedelta):
                            # Relative offset from event_start
                            return (event_start + trigger).astimezone(UTC)
                        elif isinstance(trigger, str):
                            # Fallback: try to parse ISO8601 or duration string
                            try:
                                if trigger.startswith("-") or trigger.startswith("+"):
                                    # Duration string, e.g. -PT10M
                                    # Use icalendar's vDuration parser if available
                                    from icalendar.prop import vDuration

                                    td = vDuration.from_ical(trigger)  # type: ignore[arg-type]
                                    return (event_start + td).astimezone(UTC)
                                else:
                                    # Try parsing as datetime
                                    trig_val = datetime.fromisoformat(trigger)
                                    if trig_val.tzinfo is None and local_tz is not None:
                                        trig_val = trig_val.replace(tzinfo=local_tz)
                                    return trig_val.astimezone(UTC)
                            except Exception:
                                continue
            except Exception as e:
                logger.debug(f"Failed to extract alarm trigger time: {e}")
            return None

        for event in events:
            try:
                # Convert date objects to datetime (for all-day events)
                if event.start is not None:
                    if type(event.start) is date:  # Plain date, not datetime
                        # All-day event: convert date to datetime at midnight
                        event.start = datetime.combine(event.start, datetime.min.time())
                        if local_tz is not None:
                            event.start = event.start.replace(tzinfo=local_tz)
                    elif event.start.tzinfo is None and local_tz is not None:
                        event.start = event.start.replace(tzinfo=local_tz)
                if getattr(event, "end", None) is not None:
                    end = event.end
                    if end is not None:
                        if type(end) is date:  # Plain date, not datetime
                            # All-day event end: convert date to datetime at midnight
                            end = datetime.combine(end, datetime.min.time())
                            if local_tz is not None:
                                end = end.replace(tzinfo=local_tz)
                            event.end = end
                        elif end.tzinfo is None and local_tz is not None:
                            event.end = end.replace(tzinfo=local_tz)
            except Exception:
                uid = getattr(event, "uid", "?")
                logger.debug(
                    "Failed to apply local tz to event: %s",
                    uid,
                )
        for event in events:
            if event.start and lower_bound <= event.start <= upper_bound:
                desc = str(event.description) if event.description else ""
                trigger_time = extract_trigger_time(event)
                # Only include events that have actual alarms
                if trigger_time is not None:
                    alarms.append(
                        {
                            "uid": str(event.uid),
                            "name": str(event.summary),
                            "begin": event.start,
                            "description": desc,
                            "trigger_time": trigger_time,
                        }
                    )
        return alarms

    @staticmethod
    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=5,
        jitter=backoff.full_jitter,
        on_backoff=lambda details: CalendarService._on_backoff(details),
        on_giveup=lambda details: CalendarService._on_giveup(details),
    )
    async def fetch_ics(url: str) -> str | None:
        """
        Fetches ICS content from a URL with exponential backoff retry.

        Args:
            url (str): The ICS feed URL.

        Returns:
            str | None: The ICS content as a string, or None if fetch fails.
        """
        if url.startswith("webcal://"):
            url = url.replace("webcal://", "https://", 1)

        # Use icalevents' ICalDownload to fetch and normalize iCal content.
        downloader = ICalDownload()
        content = await asyncio.to_thread(downloader.data_from_url, url, False)
        return content

    @staticmethod
    async def get_all_alarms(
        sources: list[tuple[int, str]],
        check_time: datetime | None = None,
        lookback_minutes: int | None = None,
        lookahead_minutes: int = 0,
        tzinfo: tzinfo | None = None,
    ) -> list[dict[str, Any]]:
        """
        Aggregates alarms from multiple URLs using icalevents.

        Args:
            sources (list[tuple[int, str]]): List of (source_id, url) tuples.
            check_time (datetime | None):
                Reference time for alarm calculation. Defaults to now.
            lookback_minutes (int | None):
                Minutes back to include events. Defaults to 12 hours.
            lookahead_minutes (int): Minutes ahead to include events.
            tzinfo (ZoneInfo | None): Timezone to use for parsing, if any.

        Returns:
            list[dict]: Aggregated list of alarm event dictionaries.
        """
        if check_time is None:
            check_time = datetime.now(UTC)
        if lookback_minutes is None:
            lookback_minutes = 60 * 12
        tasks = [CalendarService.fetch_ics(url) for _, url in sources]
        logger.info("Fetching ICS for %d sources", len(sources))
        results = await asyncio.gather(*tasks)
        all_alarms: list[dict[str, Any]] = []
        for (source_id, url), content in zip(sources, results, strict=False):
            if content:
                fix_icloud = "icloud.com" in url
                alarms = CalendarService.get_upcoming_alarms(
                    content,
                    check_time,
                    lookahead_minutes=lookahead_minutes,
                    lookback_minutes=lookback_minutes,
                    tzinfo=tzinfo,
                    fix_icloud=fix_icloud,
                )
                logger.info(
                    "Source %s returned %d upcoming alarms (fix_icloud=%s)",
                    source_id,
                    len(alarms),
                    fix_icloud,
                )
                for alarm in alarms:
                    alarm["uid"] = f"{source_id}:{alarm['uid']}"
                all_alarms.extend(alarms)
            else:
                logger.warning(
                    "Skipping calendar %s due to missing content.",
                    source_id,
                )
        return all_alarms

    @staticmethod
    def extract_events_from_ics(
        ics_content: str,
        source_id: int,
        window_start: datetime,
        window_end: datetime,
        fix_icloud: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Parses ICS content and extracts events within the given
        time window using icalevents. Also extracts alarm trigger_time.

        Returns:
            list[dict]: List of event dicts with keys:
                uid, event_start, event_end, summary, description,
                location, has_non_time_alarm, source_id, trigger_time.
        """
        events: list[dict[str, Any]] = []
        # Patch: Expand RRULE events for the full window, even if DTSTART is old
        ical_events = CalendarService.parse_ics_events(
            ics_content, window_start, window_end, fix_icloud=fix_icloud
        )
        expanded_events = []
        for event in ical_events:
            try:
                if hasattr(event, "recurrence_rules") and event.recurrence_rules:
                    # Defensive: If event.start < window_start, manually expand weekly events for each weekday in window
                    import re
                    from datetime import timedelta

                    rrule_str = event.recurrence_rules[0] if event.recurrence_rules else ""
                    if re.search(r"FREQ=WEEKLY", rrule_str):
                        # Extract INTERVAL parameter (default 1 if not specified)
                        interval_match = re.search(r"INTERVAL=(\d+)", rrule_str)
                        interval = int(interval_match.group(1)) if interval_match else 1
                        increment_days = 7 * interval

                        # Find weekday from DTSTART
                        dt = event.start
                        weekday = dt.weekday()
                        # Expand for each week in window
                        first_in_window = window_start
                        # Find first occurrence of this weekday >= window_start
                        days_ahead = (weekday - window_start.weekday()) % 7
                        first_occurrence = window_start + timedelta(days=days_ahead)
                        # If first_occurrence < window_start, add increment_days
                        if first_occurrence < window_start:
                            first_occurrence += timedelta(days=increment_days)
                        occ_dt = first_occurrence
                        while occ_dt <= window_end:
                            # Only add if >= dt (DTSTART)
                            if occ_dt >= dt:
                                # For recurring events, create unique UID per occurrence
                                # by appending the occurrence date (RFC 5545 RECURRENCE-ID style)
                                occurrence_uid = f"{event.uid}:{occ_dt.isoformat()}"
                                ev_copy = event.__class__(
                                    uid=occurrence_uid,
                                    start=occ_dt,
                                    end=occ_dt + (event.end - event.start) if event.end else None,
                                    summary=event.summary,
                                    description=event.description,
                                    location=event.location,
                                    raw=getattr(event, "raw", None),
                                )
                                expanded_events.append(ev_copy)
                            occ_dt += timedelta(days=increment_days)
                        continue
                expanded_events.append(event)
            except Exception:
                expanded_events.append(event)
        ical_events = expanded_events
        logger.debug(
            "Extracting events from source %s: %d events parsed by icalevents",
            source_id,
            len(ical_events),
        )
        local_tz = CalendarService._get_local_tz()

        proximity_uids = CalendarService._detect_proximity_uids(ics_content)
        logger.debug(
            "Detected %d proximity UIDs in raw ICS",
            len(proximity_uids),
        )
        logger.debug(
            "Parsed %d events from ICS for source %d",
            len(ical_events),
            source_id,
        )

        def extract_trigger_time(event: ICalEvent) -> datetime | None:
            """Extract first alarm trigger time, handling proximity alarms."""
            try:
                if not hasattr(event, "raw") or not hasattr(event.raw, "subcomponents"):  # type: ignore[attr-defined]
                    return None
                event_start = event.start
                if event_start is None:
                    return None
                if event_start.tzinfo is None and local_tz is not None:
                    event_start = event_start.replace(tzinfo=local_tz)
                for sub in getattr(event.raw, "subcomponents", []):  # type: ignore[attr-defined]
                    if getattr(sub, "name", "").upper() == "VALARM":
                        trigger = sub.get("TRIGGER")
                        if trigger is None:
                            # Check for proximity alarm (PROXIMITY:ARRIVE/DEPART)
                            proximity = sub.get("PROXIMITY")
                            if proximity is not None:
                                logger.debug(
                                    "Proximity alarm in event: %s",
                                    getattr(event, "uid", "?"),
                                )
                                # Proximity alarms fire at event start time
                                return event_start.astimezone(UTC)
                            continue
                        if hasattr(trigger, "dt"):
                            # vDDDTypes object with .dt attribute
                            trig_val = trigger.dt
                            if isinstance(trig_val, datetime):
                                # Absolute datetime
                                if trig_val.tzinfo is None and local_tz is not None:
                                    trig_val = trig_val.replace(tzinfo=local_tz)
                                return trig_val.astimezone(UTC)
                            elif isinstance(trig_val, timedelta):
                                # Relative offset from event_start
                                return (event_start + trig_val).astimezone(UTC)
                        elif isinstance(trigger, timedelta):
                            return (event_start + trigger).astimezone(UTC)
                        elif isinstance(trigger, str):
                            try:
                                if trigger.startswith("-") or trigger.startswith("+"):
                                    from icalendar.prop import vDuration

                                    td = vDuration.from_ical(trigger)  # type: ignore[arg-type]
                                    return (event_start + td).astimezone(UTC)
                                else:
                                    trig_val = datetime.fromisoformat(trigger)
                                    if trig_val.tzinfo is None and local_tz is not None:
                                        trig_val = trig_val.replace(tzinfo=local_tz)
                                    return trig_val.astimezone(UTC)
                            except Exception:
                                continue
            except Exception as e:
                logger.debug(f"Failed to extract alarm trigger time: {e}")
            return None

        for event in ical_events:
            # Determine original TZID from raw component or from tzinfo
            tzid: str | None = None
            try:
                raw = getattr(event, "raw", None)
                if raw is not None:
                    try:
                        dtstart_prop = raw.get("DTSTART")
                        if dtstart_prop is not None:
                            params = getattr(dtstart_prop, "params", {})
                            if params and "TZID" in params:
                                tzid = params.get("TZID")
                    except Exception:
                        # ignore and try other methods
                        pass
                    if not tzid:
                        try:
                            tz_prop = raw.get("TZID")
                            if tz_prop:
                                tzid = str(tz_prop)
                        except Exception:
                            pass
                # Fallback: derive from event.start.tzinfo if available
                if not tzid and getattr(event, "start", None) is not None:
                    try:
                        start_tz = event.start.tzinfo
                        if start_tz is not None:
                            tzid = (
                                getattr(start_tz, "key", None)
                                or getattr(start_tz, "zone", None)
                                or start_tz.tzname(event.start)
                            )
                    except Exception:
                        tzid = None
            except Exception:
                tzid = None

            events.append(
                {
                    "uid": str(event.uid),
                    "event_start": event.start,
                    "event_end": event.end,
                    "summary": str(event.summary),
                    "description": str(event.description),
                    "location": str(event.location),
                    "has_non_time_alarm": str(event.uid) in proximity_uids,
                    "source_id": source_id,
                    "tzid": tzid,
                    "all_day": getattr(event, "all_day", False),  # Track all-day events
                    "trigger_time": extract_trigger_time(event)
                    if extract_trigger_time(event) is not None
                    else CalendarService._fallback_trigger_from_raw(ics_content, event),
                }
            )
        return events

    @staticmethod
    def _fallback_trigger_from_raw(ics_content: str, event: ICalEvent) -> datetime | None:
        """
        If `extract_trigger_time` failed, attempt to compute trigger_time by
        parsing the raw ICS content for the event's UID and interpreting the
        TRIGGER value. Returns a UTC-aware datetime or None.
        """
        try:
            uid = str(getattr(event, "uid", ""))
            trig = CalendarService._extract_trigger_from_raw(ics_content, uid)
            if not trig:
                return None
            local_tz = CalendarService._get_local_tz()
            if trig == "PROXIMITY":
                ev_start = event.start
                if ev_start is None:
                    return None
                if ev_start.tzinfo is None and local_tz is not None:
                    ev_start = ev_start.replace(tzinfo=local_tz)
                return ev_start.astimezone(UTC)
            # trig is a string: could be duration (-PT10M) or datetime
            if trig.startswith("-") or trig.startswith("+"):
                try:
                    from icalendar.prop import vDuration

                    td = vDuration.from_ical(trig)  # type: ignore[arg-type]
                    ev_start = event.start
                    if ev_start is None:
                        return None
                    if ev_start.tzinfo is None and local_tz is not None:
                        ev_start = ev_start.replace(tzinfo=local_tz)
                    return (ev_start + td).astimezone(UTC)
                except Exception:
                    return None
            else:
                # Try absolute datetime
                try:
                    dt = datetime.fromisoformat(trig)
                    if dt.tzinfo is None and local_tz is not None:
                        dt = dt.replace(tzinfo=local_tz)
                    return dt.astimezone(UTC)
                except Exception:
                    return None
        except Exception:
            return None

    @staticmethod
    def _get_or_create_sync_status(
        session: Session,
        source_id: int,
    ) -> CalendarSyncStatusEntry:
        sync_status = session.exec(
            select(CalendarSyncStatusEntry).where(
                CalendarSyncStatusEntry.calendar_source_id == source_id
            )
        ).first()

        if not sync_status:
            sync_status = CalendarSyncStatusEntry(calendar_source_id=source_id)
            session.add(sync_status)
            try:
                session.commit()
                session.refresh(sync_status)
            except Exception:
                # Handle race condition: another thread may have created the entry
                session.rollback()
                sync_status = session.exec(
                    select(CalendarSyncStatusEntry).where(
                        CalendarSyncStatusEntry.calendar_source_id == source_id
                    )
                ).first()
                if not sync_status:
                    # If still not found, re-raise the original exception
                    raise

        return sync_status

    @staticmethod
    def _mark_syncing(
        session: Session,
        sync_status: CalendarSyncStatusEntry,
    ) -> None:
        sync_status.sync_status = CalendarSyncStatus.SYNCING
        session.add(sync_status)
        session.commit()

    @staticmethod
    def _handle_fetch_failure(
        session: Session,
        sync_status: CalendarSyncStatusEntry,
        utc_now: datetime,
        source_id: int,
        label: str,
    ) -> None:
        sync_status.sync_status = CalendarSyncStatus.FAILED
        sync_status.error_count += 1
        sync_status.last_error_at = utc_now
        sync_status.error_message = "Failed to fetch ICS after 5 attempts"
        session.add(sync_status)
        session.commit()
        logger.warning(f"Failed to sync calendar {source_id}: {label}")

    @staticmethod
    def _clear_existing_cache(session: Session, source_id: int) -> None:
        existing = session.exec(
            select(CalendarEventCache).where(CalendarEventCache.calendar_source_id == source_id)
        ).all()
        for existing_event in existing:
            session.delete(existing_event)
        session.flush()

    @staticmethod
    def _select_latest_by_uid(
        events: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """
        Deduplicate events by UID, keeping the latest occurrence.

        For recurring events already expanded by icalevents (multiple occurrences
        with same UID but different start dates), we need a composite key that
        includes both UID and start date to preserve all occurrences.
        """
        latest_by_key: dict[tuple[str, datetime], dict[str, Any]] = {}

        for event in events:
            uid = event["uid"]
            ev_start = event.get("event_start")

            # Create composite key: UID + start date (unique per occurrence)
            # This way, recurring events keep all their occurrences
            if isinstance(ev_start, datetime):
                key = (uid, ev_start.date())  # Group by date, not full datetime
            else:
                key = (uid, ev_start)  # Fallback for non-datetime starts

            if key not in latest_by_key:
                latest_by_key[key] = event
                continue

            existing = latest_by_key[key]
            # Only replace if this event is "later" (for same date occurrence)
            if event["event_end"] > existing["event_end"] or (
                event["event_end"] == existing["event_end"]
                and event["event_start"] > existing["event_start"]
            ):
                latest_by_key[key] = event

        # Flatten back to dict keyed by UID only (for backwards compatibility)
        # But now we have all occurrences due to the composite key
        result: dict[str, dict[str, Any]] = {}
        for (uid, _date), event in latest_by_key.items():
            # Use a composite key that includes the occurrence date
            composite_uid = (
                f"{uid}#{event['event_start'].isoformat()}"
                if isinstance(event["event_start"], datetime)
                else uid
            )
            result[composite_uid] = event

        return result

    @staticmethod
    def _add_cache_entries(
        session: Session,
        latest_by_uid: dict[str, dict[str, Any]],
        source: CalendarSource | None = None,
        source_id: int | None = None,
    ) -> None:
        # Backwards-compatible: callers may pass either a CalendarSource
        # object (new) or a source_id int (older tests/calls). Resolve to
        # a CalendarSource instance.
        if isinstance(source, int):
            source_id = source
            source = None
        if source is None and source_id is not None:
            source = session.get(CalendarSource, source_id)
        if source is None:
            # If no CalendarSource row exists for this id (tests may pass a raw id),
            # we'll still proceed using the numeric source_id for calendar_source_id.
            if source_id is None:
                raise ValueError("Calendar source not provided to _add_cache_entries")

        # Determine calendar_source_id for DB entries
        if source is not None:
            try:
                calendar_source_id = source.id
            except Exception:
                # Fallback if a raw int slipped through as `source`
                calendar_source_id = int(source)
        else:
            calendar_source_id = source_id

        from app.db.models import CalendarEventCache

        for uid, event in latest_by_uid.items():
            try:
                # All event times are stored in UTC for consistency.
                # Original timezone is preserved in event_tz metadata.
                ev_start = event.get("event_start")
                ev_end = event.get("event_end")
                tzid = event.get("tzid")
                is_all_day = event.get("all_day", False)
                local_tz = CalendarService._get_local_tz()

                # Convert to UTC if timezone-aware; if naive, attach timezone first
                try:
                    if isinstance(ev_start, datetime) and ev_start.tzinfo is None and tzid:
                        ev_start = ev_start.replace(tzinfo=ZoneInfo(tzid))
                    elif (
                        isinstance(ev_start, datetime)
                        and ev_start.tzinfo is None
                        and local_tz is not None
                    ):
                        ev_start = ev_start.replace(tzinfo=local_tz)
                    # Convert to UTC
                    if isinstance(ev_start, datetime) and ev_start.tzinfo is not None:
                        ev_start = ensure_utc_aware(ev_start)
                        # Fix for all-day events: icalevents returns them at midnight UTC,
                        # which shifts to the previous day when converted to negative UTC offsets.
                        # Shift all-day events to noon UTC so they display correctly in all timezones.
                        if is_all_day and ev_start.hour == 0 and ev_start.minute == 0:
                            ev_start = ev_start.replace(hour=12)
                except Exception:
                    pass

                try:
                    if isinstance(ev_end, datetime) and ev_end.tzinfo is None and tzid:
                        ev_end = ev_end.replace(tzinfo=ZoneInfo(tzid))
                    elif (
                        isinstance(ev_end, datetime)
                        and ev_end.tzinfo is None
                        and local_tz is not None
                    ):
                        ev_end = ev_end.replace(tzinfo=local_tz)
                    # Convert to UTC
                    if isinstance(ev_end, datetime) and ev_end.tzinfo is not None:
                        ev_end = ensure_utc_aware(ev_end)
                        # Fix for all-day events: shift end time to noon UTC as well
                        if is_all_day and ev_end.hour == 0 and ev_end.minute == 0:
                            ev_end = ev_end.replace(hour=12)
                except Exception:
                    pass
            except Exception:
                pass

            # Trigger time is already converted to UTC in extract_trigger_time()
            trigger_time = event.get("trigger_time")
            if trigger_time is not None:
                try:
                    trigger_time = ensure_utc_aware(trigger_time)
                except Exception:
                    pass

            # Determine if we should add a default midnight alarm for events without VALARM
            optional_trigger_flag = False
            try:
                use_default_alarm = (
                    bool(getattr(source, "default_alarm_for_all_events", False))
                    if source is not None
                    else False
                )
            except Exception:
                use_default_alarm = False

            if trigger_time is None and use_default_alarm:
                # Compute midnight at event start's date in the event timezone (or local tz)
                try:
                    ev_start_orig = event.get("event_start")
                    if ev_start_orig is not None:
                        local_tz = CalendarService._get_local_tz()
                        if isinstance(ev_start_orig, datetime):
                            midnight = datetime.combine(ev_start_orig.date(), datetime.min.time())
                            if ev_start_orig.tzinfo is not None:
                                midnight = midnight.replace(tzinfo=ev_start_orig.tzinfo)
                            elif local_tz is not None:
                                midnight = midnight.replace(tzinfo=local_tz)
                        else:
                            # ev_start_orig likely a date
                            midnight = datetime.combine(ev_start_orig, datetime.min.time())
                            if local_tz is not None:
                                midnight = midnight.replace(tzinfo=local_tz)
                        trigger_time = ensure_utc_aware(midnight)
                        optional_trigger_flag = True
                except Exception:
                    optional_trigger_flag = False

            # For recurring events, we may have multiple occurrences with the same UID
            # but different start times (e.g., Feb 13 and Feb 27 for biweekly events).
            # Try to find and update existing entry first, or insert if none found.
            try:
                existing = session.exec(
                    select(CalendarEventCache).where(
                        (CalendarEventCache.calendar_source_id == calendar_source_id)
                        & (CalendarEventCache.uid == uid)
                    )
                ).first()

                if existing:
                    # Update existing entry
                    existing.event_start = cast(Any, ev_start)
                    existing.event_end = cast(Any, ev_end)
                    existing.event_tz = tzid
                    existing.summary = event["summary"]
                    existing.description = event["description"]
                    existing.location = event["location"]
                    # Persist whether this was an all-day event
                    try:
                        existing.all_day = bool(event.get("all_day", False))
                    except Exception:
                        existing.all_day = False
                    existing.trigger_time = trigger_time
                    existing.optional_trigger = optional_trigger_flag
                    session.add(existing)
                else:
                    # Insert new entry
                    cache_entry = CalendarEventCache(
                        calendar_source_id=calendar_source_id,
                        uid=uid,
                        event_start=cast(Any, ev_start),
                        event_end=cast(Any, ev_end),
                        event_tz=tzid,
                        summary=event["summary"],
                        description=event["description"],
                        location=event["location"],
                        all_day=bool(event.get("all_day", False)),
                        trigger_time=trigger_time,
                        optional_trigger=optional_trigger_flag,
                    )
                    session.add(cache_entry)
            except Exception as e:
                # If update fails, still try to add as new
                cache_entry = CalendarEventCache(
                    calendar_source_id=calendar_source_id,
                    uid=uid,
                    event_start=cast(Any, ev_start),
                    event_end=cast(Any, ev_end),
                    event_tz=tzid,
                    summary=event["summary"],
                    description=event["description"],
                    location=event["location"],
                    trigger_time=trigger_time,
                    optional_trigger=optional_trigger_flag,
                )
                session.add(cache_entry)

    @staticmethod
    def _finalize_success(
        session: Session,
        sync_status: CalendarSyncStatusEntry,
        utc_now: datetime,
        events: list[dict[str, Any]],
        source: CalendarSource,
    ) -> None:
        sync_status.sync_status = CalendarSyncStatus.SUCCESS
        sync_status.last_synced_at = utc_now
        sync_status.error_count = 0
        sync_status.error_message = ""
        session.add(sync_status)
        session.commit()
        logger.info(
            "Successfully synced calendar %s (%s): %d events",
            source.id,
            source.label,
            len(events),
        )

    @staticmethod
    def _finalize_failure(
        session: Session,
        sync_status: CalendarSyncStatusEntry,
        utc_now: datetime,
        e: Exception,
        source_id: int,
    ) -> None:
        logger.error(f"Error syncing calendar {source_id}: {e}")
        sync_status.sync_status = CalendarSyncStatus.FAILED
        sync_status.error_count += 1
        sync_status.last_error_at = utc_now
        # Security: Sanitize error message to avoid exposing sensitive information
        # Full error details are logged above for debugging
        error_str = str(e)
        # Remove potential credentials from URLs in error messages
        import re

        sanitized_error = re.sub(
            r"(https?://)[^:@/\s]+:[^@/\s]+@",  # Remove user:pass@ from URLs
            r"\1***:***@",
            error_str,
        )
        # Limit error message length
        if len(sanitized_error) > 200:
            sanitized_error = sanitized_error[:197] + "..."
        sync_status.error_message = sanitized_error
        session.add(sync_status)
        session.commit()

    @staticmethod
    async def _sync_single_source(
        session: Session,
        source: CalendarSource,
        utc_now: datetime,
        window_start: datetime,
        window_end: datetime,
    ) -> None:
        """
        Sync a single calendar source: fetch, parse, upsert cache,
        and update status.
        """
        assert source.id is not None
        source_id = source.id

        sync_status = CalendarService._get_or_create_sync_status(session, source_id)
        CalendarService._mark_syncing(session, sync_status)

        try:
            ics_content = await CalendarService.fetch_ics(source.url)

            if ics_content is None:
                CalendarService._handle_fetch_failure(
                    session, sync_status, utc_now, source_id, source.label
                )
                return

            fix_icloud = "icloud.com" in source.url
            events = CalendarService.extract_events_from_ics(
                ics_content,
                source_id,
                window_start,
                window_end,
                fix_icloud=fix_icloud,
            )

            # Remove cached events for this source (we'll re-insert)
            CalendarService._clear_existing_cache(session, source_id)

            latest_by_uid = CalendarService._select_latest_by_uid(events)
            CalendarService._add_cache_entries(
                session,
                latest_by_uid,
                source,
            )

            session.commit()

            CalendarService._finalize_success(
                session,
                sync_status,
                utc_now,
                events,
                source,
            )

        except Exception as e:
            CalendarService._finalize_failure(
                session,
                sync_status,
                utc_now,
                e,
                source_id,
            )

    @staticmethod
    async def sync_calendar_events(session: Session) -> None:
        """
        Background task: Fetches all calendar sources and caches events
        within the 1-week window. Automatically purges events outside the
        window and handles errors gracefully.
        """
        utc_now = datetime.now(UTC)
        window_start = utc_now - timedelta(days=7)
        window_end = utc_now + timedelta(days=7)

        sources = session.exec(select(CalendarSource)).all()
        if not sources:
            logger.info("No calendar sources configured.")
            return

        logger.info(
            "Starting background sync for %d calendar sources.",
            len(sources),
        )

        for source in sources:
            if not source.id:
                continue

            await CalendarService._sync_single_source(
                session, source, utc_now, window_start, window_end
            )

        # After syncing all sources, assign unique-ish offsets (5-10 minutes)
        # Shuffle offsets and assign one per status; cycle if more sources exist.
        try:
            statuses = session.exec(select(CalendarSyncStatusEntry)).all()
            offsets = [5, 6, 7, 8, 9, 10]
            random.shuffle(offsets)
            idx = 0
            for st in statuses:
                try:
                    offset = offsets[idx % len(offsets)]
                    st.next_sync_at = utc_now + timedelta(minutes=10 + offset)
                    session.add(st)
                    idx += 1
                except Exception:
                    logger.exception(
                        "Failed to assign next_sync_at for status %s",
                        getattr(st, "id", "?"),
                    )
            session.commit()
        except Exception:
            logger.exception("Failed to assign next_sync_at after calendar sync")

        # Auto-cleanup: Purge dismissed events outside the window
        try:
            dismissed_col = cast(Any, AlarmEvent.dismissed_at)
            trigger_col = cast(Any, AlarmEvent.trigger_time)
            old_dismissed = session.exec(
                select(AlarmEvent).where(
                    and_(
                        dismissed_col.isnot(None),
                        trigger_col < window_start,
                    )
                )
            ).all()

            for alarm in old_dismissed:
                session.delete(alarm)

            if old_dismissed:
                session.commit()
                logger.info(
                    "Purged %d dismissed events outside window",
                    len(old_dismissed),
                )
        except Exception as e:
            logger.warning(f"Error purging old dismissed events: {e}")

        logger.info("Background sync completed.")

#!/usr/bin/env python3
# ruff: noqa
import asyncio
import logging
import os
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

        Uses the icalevents library for parsing.

        Args:
            ics_content (str): The raw ICS data as a string.
            start (datetime): Start of the window for event extraction.
            end (datetime): End of the window for event extraction.
            tzinfo (ZoneInfo | None): Timezone to use for parsing, if any.
            fix_icloud (bool):
                Whether to apply iCloud/Apple-specific parsing
                workarounds.

        Returns:
            list[ICalEvent]: List of parsed calendar events.
        """
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
                    return events_fn(**kwargs)
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
            return events_fn(**base_kwargs)
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
        # Ensure events have timezone info; if naive, apply local tz fallback
        local_tz = CalendarService._get_local_tz()
        for event in events:
            try:
                if event.start is not None:
                    start = event.start
                    if start.tzinfo is None and local_tz is not None:
                        event.start = start.replace(tzinfo=local_tz)
                if getattr(event, "end", None) is not None:
                    end = event.end
                    if end is not None:
                        if end.tzinfo is None and local_tz is not None:
                            event.end = end.replace(tzinfo=local_tz)
            except Exception:
                uid = getattr(event, "uid", "?")
                logger.debug(
                    "Failed to apply local tz to event: %s",
                    uid,
                )
        for event in events:
            # event is an ICalEvent
            if event.start and lower_bound <= event.start <= upper_bound:
                desc = str(event.description) if event.description else ""
                alarms.append(
                    {
                        "uid": str(event.uid),
                        "name": str(event.summary),
                        "begin": event.start,
                        "description": desc,
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
        time window using icalevents.

        Args:
            ics_content (str): The raw ICS data as a string.
            source_id (int): The calendar source ID.
            window_start (datetime): Start of the window for event extraction.
            window_end (datetime): End of the window for event extraction.
            fix_icloud (bool):
                Whether to apply iCloud/Apple-specific parsing
                workarounds.

        Returns:
            list[dict]: List of event dicts with keys:
                uid, event_start, event_end, summary, description,
                location, has_non_time_alarm, source_id.
        """
        events: list[dict[str, Any]] = []
        ical_events = CalendarService.parse_ics_events(
            ics_content, window_start, window_end, fix_icloud=fix_icloud
        )
        logger.debug(
            "Extracting events from source %s: %d events parsed by icalevents",
            source_id,
            len(ical_events),
        )
        # Apply local tz fallback for naive datetimes returned by parser
        local_tz = CalendarService._get_local_tz()
        for event in ical_events:
            try:
                if event.start is not None:
                    start = event.start
                    if start.tzinfo is None and local_tz is not None:
                        event.start = start.replace(tzinfo=local_tz)
                if getattr(event, "end", None) is not None:
                    end = event.end
                    if end is not None:
                        if end.tzinfo is None and local_tz is not None:
                            event.end = end.replace(tzinfo=local_tz)
            except Exception:
                logger.debug(
                    "Failed to apply local tz to event during extract: %s",
                    getattr(event, "uid", "?"),
                )
        proximity_uids = CalendarService._detect_proximity_uids(ics_content)
        logger.debug(
            "Detected %d proximity UIDs in raw ICS",
            len(proximity_uids),
        )
        for event in ical_events:
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
                }
            )
        return events

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
            session.commit()
            session.refresh(sync_status)

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
    def _select_latest_by_uid(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        latest_by_uid: dict[str, dict[str, Any]] = {}
        for event in events:
            uid = event["uid"]
            if uid not in latest_by_uid:
                latest_by_uid[uid] = event
                continue
            existing = latest_by_uid[uid]
            if event["event_end"] > existing["event_end"] or (
                event["event_end"] == existing["event_end"]
                and event["event_start"] > existing["event_start"]
            ):
                latest_by_uid[uid] = event
        return latest_by_uid

    @staticmethod
    def _add_cache_entries(
        session: Session,
        latest_by_uid: dict[str, dict[str, Any]],
        source_id: int,
    ) -> None:
        for uid, event in latest_by_uid.items():
            try:
                start_utc = (
                    ensure_utc_aware(event["event_start"])
                    if event["event_start"] is not None
                    else None
                )
            except Exception:
                start_utc = event["event_start"]
            try:
                end_utc = (
                    ensure_utc_aware(event["event_end"]) if event["event_end"] is not None else None
                )
            except Exception:
                end_utc = event["event_end"]

            cache_entry = CalendarEventCache(
                calendar_source_id=source_id,
                uid=uid,
                event_start=cast(Any, start_utc),
                event_end=cast(Any, end_utc),
                summary=event["summary"],
                description=event["description"],
                location=event["location"],
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
        sync_status.next_sync_at = utc_now + timedelta(minutes=10)
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
        sync_status.error_message = str(e)
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
                source_id,
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

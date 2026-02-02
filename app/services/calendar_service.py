import asyncio
import logging
from datetime import UTC, datetime, timedelta

import backoff
import httpx
from icalendar import Calendar
from sqlmodel import Session, select

from app.db.models import (
    AlarmEvent,
    CalendarEventCache,
    CalendarSource,
    CalendarSyncStatus,
    CalendarSyncStatusEntry,
)

logger = logging.getLogger(__name__)


class CalendarService:
    @staticmethod
    def _on_backoff(details):
        """Callback for backoff retry attempts."""
        tries = details.get("tries", 0)
        exception = details.get("exception")
        wait = details.get("wait", 0)
        logger.info(
            f"Retrying calendar fetch (attempt {tries}/5): "
            f"Exception: {exception.__class__.__name__}, "
            f"waiting {wait:.1f}s"
        )

    @staticmethod
    def _on_giveup(details):
        """Callback when backoff gives up after max retries."""
        tries = details.get("tries", 0)
        exception = details.get("exception")
        logger.warning(
            f"Failed to fetch ICS after {tries} attempts: "
            f"{exception.__class__.__name__}: {exception}"
        )

    @staticmethod
    def parse_ics(ics_content: str) -> Calendar | None:
        """Parses ICS content string into a Calendar object."""
        try:
            return Calendar.from_ical(ics_content)
        except Exception as e:
            logger.warning("Failed to parse ICS content: %s", e)
            return None

    @staticmethod
    def get_upcoming_alarms(
        calendar: Calendar,
        check_time: datetime,
        lookahead_minutes: int = 0,
        lookback_minutes: int = 60 * 12,
        tz_offset_minutes: int | None = None,
    ) -> list[dict]:
        """
        Returns a list of events starting within the next `lookahead_minutes`
        OR that started in the last `lookback_minutes` (e.g. today).
        """
        alarms = []
        if not calendar:
            return alarms

        # Ensure check_time is aware (UTC)
        if check_time.tzinfo is None:
            check_time = check_time.replace(tzinfo=UTC)

        for component in calendar.walk():
            if component.name == "VEVENT":
                summary = component.get("summary")
                description = component.get("description")
                uid = component.get("uid")
                dtstart = component.get("dtstart")

                if not dtstart:
                    continue

                event_start = dtstart.dt

                # Normalize event_start to datetime (handle date objects)
                if not isinstance(event_start, datetime):
                    event_start = datetime.combine(event_start, datetime.min.time())
                if event_start.tzinfo is None:
                    if tz_offset_minutes is not None:
                        # Convert device-local time to UTC by adding the offset
                        # (offset is negative when ahead of UTC, e.g., -120 for UTC+2,
                        #  so adding it effectively subtracts the hours we're ahead)
                        event_start = (event_start + timedelta(minutes=tz_offset_minutes)).replace(
                            tzinfo=UTC
                        )
                    else:
                        event_start = event_start.replace(tzinfo=UTC)

                # Logic: Is event inside the window [now - lookback, now + lookahead]?
                lower_bound = check_time - timedelta(minutes=lookback_minutes)
                upper_bound = check_time + timedelta(minutes=lookahead_minutes)

                if lower_bound <= event_start <= upper_bound:
                    alarms.append(
                        {
                            "uid": str(uid),
                            "name": str(summary),
                            "begin": event_start,
                            "description": str(description) if description else "",
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
        """Fetches ICS content from a URL with exponential backoff retry."""
        if url.startswith("webcal://"):
            url = url.replace("webcal://", "https://", 1)

        headers = {
            "User-Agent": "Espace-Image/1.0 (+https://github.com/pmgagne/espace-image)",
            "Accept": "text/calendar,*/*;q=0.8",
        }

        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.text

    @staticmethod
    async def get_all_alarms(
        sources: list[tuple[int, str]],
        check_time: datetime | None = None,
        lookback_minutes: int | None = None,
        lookahead_minutes: int = 0,
        tz_offset_minutes: int | None = None,
    ) -> list[dict]:
        """Aggregates alarms from multiple URLs."""
        if check_time is None:
            # Always use UTC aware datetime for comparison with ics/arrow
            check_time = datetime.now(UTC)

        if lookback_minutes is None:
            lookback_minutes = 60 * 12

        tasks = [CalendarService.fetch_ics(url) for _, url in sources]
        results = await asyncio.gather(*tasks)

        all_alarms = []
        for (source_id, _), content in zip(sources, results, strict=False):
            if content:
                cal = CalendarService.parse_ics(content)
                if not cal:
                    logger.warning("Skipping calendar %s due to parse failure.", source_id)
                    continue
                alarms = CalendarService.get_upcoming_alarms(
                    cal,
                    check_time,
                    lookahead_minutes=lookahead_minutes,
                    lookback_minutes=lookback_minutes,
                    tz_offset_minutes=tz_offset_minutes,
                )
                for alarm in alarms:
                    alarm["uid"] = f"{source_id}:{alarm['uid']}"
                all_alarms.extend(alarms)
            else:
                logger.warning("Skipping calendar %s due to missing content.", source_id)

        return all_alarms

    @staticmethod
    def extract_events_from_ics(
        ics_content: str, source_id: int, window_start: datetime, window_end: datetime
    ) -> list[dict]:
        """
        Parses ICS content and extracts events within the given time window.
        Returns list of event dicts with keys: uid, event_start, event_end, summary, description, location.
        """
        events = []
        cal = CalendarService.parse_ics(ics_content)
        if not cal:
            return events

        for component in cal.walk():
            if component.name == "VEVENT":
                uid = component.get("uid")
                summary = component.get("summary", "")
                description = component.get("description", "")
                location = component.get("location", "")
                dtstart = component.get("dtstart")
                dtend = component.get("dtend")

                if not dtstart:
                    continue

                event_start = dtstart.dt
                event_end = dtend.dt if dtend else event_start

                # Normalize to datetime if date object
                if not isinstance(event_start, datetime):
                    event_start = datetime.combine(event_start, datetime.min.time(), tzinfo=UTC)
                elif event_start.tzinfo is None:
                    event_start = event_start.replace(tzinfo=UTC)

                if not isinstance(event_end, datetime):
                    event_end = datetime.combine(event_end, datetime.min.time(), tzinfo=UTC)
                elif event_end.tzinfo is None:
                    event_end = event_end.replace(tzinfo=UTC)

                # Check if event overlaps with window [window_start, window_end]
                if event_start <= window_end and event_end >= window_start:
                    events.append(
                        {
                            "uid": str(uid),
                            "event_start": event_start,
                            "event_end": event_end,
                            "summary": str(summary),
                            "description": str(description),
                            "location": str(location),
                            "source_id": source_id,
                        }
                    )

        return events

    @staticmethod
    async def _sync_single_source(
        session: Session,
        source: CalendarSource,
        utc_now: datetime,
        window_start: datetime,
        window_end: datetime,
    ) -> None:
        """Sync a single calendar source: fetch, parse, upsert cache, update status."""
        source_id = source.id

        # Get or create sync status
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

        # Mark as syncing
        sync_status.sync_status = CalendarSyncStatus.SYNCING
        session.add(sync_status)
        session.commit()

        try:
            ics_content = await CalendarService.fetch_ics(source.url)

            if ics_content is None:
                sync_status.sync_status = CalendarSyncStatus.FAILED
                sync_status.error_count += 1
                sync_status.last_error_at = utc_now
                sync_status.error_message = "Failed to fetch ICS after 5 attempts"
                session.add(sync_status)
                session.commit()
                logger.warning(f"Failed to sync calendar {source_id}: {source.label}")
                return

            events = CalendarService.extract_events_from_ics(
                ics_content, source_id, window_start, window_end
            )

            # Remove cached events for this source (we'll re-insert)
            existing = session.exec(
                select(CalendarEventCache).where(CalendarEventCache.calendar_source_id == source_id)
            ).all()

            for existing_event in existing:
                session.delete(existing_event)

            session.flush()

            latest_by_uid: dict[str, dict] = {}
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

            for uid, event in latest_by_uid.items():
                cache_entry = CalendarEventCache(
                    calendar_source_id=source_id,
                    uid=uid,
                    event_start=event["event_start"],
                    event_end=event["event_end"],
                    summary=event["summary"],
                    description=event["description"],
                    location=event["location"],
                )
                session.add(cache_entry)

            session.commit()

            sync_status.sync_status = CalendarSyncStatus.SUCCESS
            sync_status.last_synced_at = utc_now
            sync_status.next_sync_at = utc_now + timedelta(minutes=10)
            sync_status.error_count = 0
            sync_status.error_message = ""
            session.add(sync_status)
            session.commit()

            logger.info(
                f"Successfully synced calendar {source_id} ({source.label}): {len(events)} events"
            )

        except Exception as e:
            logger.error(f"Error syncing calendar {source_id}: {e}")
            sync_status.sync_status = CalendarSyncStatus.FAILED
            sync_status.error_count += 1
            sync_status.last_error_at = utc_now
            sync_status.error_message = str(e)
            session.add(sync_status)
            session.commit()

    @staticmethod
    async def sync_calendar_events(session: Session) -> None:
        """
        Background task: Fetches all calendar sources and caches events within the 1-week window.
        Automatically purges events outside the window and handles errors gracefully.
        """
        utc_now = datetime.now(UTC)
        window_start = utc_now - timedelta(days=7)
        window_end = utc_now + timedelta(days=7)

        sources = session.exec(select(CalendarSource)).all()
        if not sources:
            logger.info("No calendar sources configured.")
            return

        logger.info(f"Starting background sync for {len(sources)} calendar sources.")

        for source in sources:
            if not source.id:
                continue

            await CalendarService._sync_single_source(
                session, source, utc_now, window_start, window_end
            )

        # Auto-cleanup: Purge dismissed events outside the window
        try:
            old_dismissed = session.exec(
                select(AlarmEvent).where(
                    (AlarmEvent.dismissed_at.is_not(None))
                    & (AlarmEvent.trigger_time < window_start)
                )
            ).all()

            for alarm in old_dismissed:
                session.delete(alarm)

            if old_dismissed:
                session.commit()
                logger.info(f"Purged {len(old_dismissed)} dismissed events outside window")
        except Exception as e:
            logger.warning(f"Error purging old dismissed events: {e}")

        logger.info("Background sync completed.")

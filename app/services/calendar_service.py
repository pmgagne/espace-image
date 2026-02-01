import asyncio
import logging
from datetime import UTC, datetime, timedelta

import httpx
from icalendar import Calendar

logger = logging.getLogger(__name__)


class CalendarService:
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
    async def fetch_ics(url: str) -> str | None:
        """Fetches ICS content from a URL."""
        if url.startswith("webcal://"):
            url = url.replace("webcal://", "https://", 1)

        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
        except Exception as e:
            logger.warning("Failed to fetch ICS from %s: %s", url, e)
            return None

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

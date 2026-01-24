import asyncio
from datetime import UTC, datetime, timedelta

import httpx
from icalendar import Calendar


class CalendarService:
    @staticmethod
    def parse_ics(ics_content: str) -> Calendar | None:
        """Parses ICS content string into a Calendar object."""
        try:
            return Calendar.from_ical(ics_content)
        except Exception as e:
            print(f"Error parsing ICS: {e}")
            return None

    @staticmethod
    def get_upcoming_alarms(
        calendar: Calendar,
        check_time: datetime,
        lookahead_minutes: int = 15,
        lookback_minutes: int = 60 * 12,
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
                    event_start = datetime.combine(event_start, datetime.min.time(), tzinfo=UTC)
                elif event_start.tzinfo is None:
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
            print(f"Error fetching ICS from {url}: {e}")
            return None

    @staticmethod
    async def get_all_alarms(urls: list[str], check_time: datetime | None = None) -> list[dict]:
        """Aggregates alarms from multiple URLs."""
        if check_time is None:
            # Always use UTC aware datetime for comparison with ics/arrow
            check_time = datetime.now(UTC)

        tasks = [CalendarService.fetch_ics(url) for url in urls]
        results = await asyncio.gather(*tasks)

        all_alarms = []
        for content in results:
            if content:
                cal = CalendarService.parse_ics(content)
                # Use default lookback (12h) and lookahead (15m)
                alarms = CalendarService.get_upcoming_alarms(cal, check_time)
                all_alarms.extend(alarms)

        return all_alarms

from ics import Calendar
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import httpx

class CalendarService:
    @staticmethod
    def parse_ics(ics_content: str) -> Calendar:
        """Parses ICS content string into a Calendar object."""
        return Calendar(ics_content)

    @staticmethod
    def get_upcoming_alarms(calendar: Calendar, check_time: datetime, lookahead_minutes: int = 15) -> List[dict]:
        """
        Returns a list of events starting within the next `lookahead_minutes`.
        """
        alarms = []
        # Ensure check_time is aware if possible, or naive if calendar is naive. 
        # ics library usually handles timezones. We will try to normalize to UTC for comparison.
        
        for event in calendar.events:
            if not event.begin:
                continue
                
            # Convert event.begin to the same timezone info as check_time for comparison
            # Ideally both should be UTC.
            event_start = event.begin
            
            # Simple check: Is the event start time between now and now + lookahead?
            # We assume check_time is "now"
            
            # Check if event is in the future relative to check_time
            if event_start > check_time:
                # Check if it's within the window
                diff = event_start - check_time
                if diff <= timedelta(minutes=lookahead_minutes):
                    alarms.append({
                        "uid": event.uid,
                        "name": event.name,
                        "begin": event_start,
                        "description": event.description
                    })
                    
        return alarms

    @staticmethod
    async def fetch_ics(url: str) -> Optional[str]:
        """Fetches ICS content from a URL."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
        except Exception as e:
            print(f"Error fetching ICS: {e}")
            return None

import pytest
from datetime import datetime, timedelta, timezone
from app.services.calendar_service import CalendarService

# Sample ICS content
SAMPLE_ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//hacksw/handcal//NONSGML v1.0//EN
BEGIN:VEVENT
UID:event1@example.com
DTSTAMP:20230101T000000Z
DTSTART:20260116T100000Z
DTEND:20260116T110000Z
SUMMARY:Meeting in 10 mins
END:VEVENT
BEGIN:VEVENT
UID:event2@example.com
DTSTAMP:20230101T000000Z
DTSTART:20260116T120000Z
DTEND:20260116T130000Z
SUMMARY:Lunch later
END:VEVENT
END:VCALENDAR"""

def test_parse_ics():
    calendar = CalendarService.parse_ics(SAMPLE_ICS)
    assert len(calendar.events) == 2
    
def test_get_upcoming_alarms():
    calendar = CalendarService.parse_ics(SAMPLE_ICS)
    
    # Mock "now" as 2026-01-16 09:50:00 UTC (10 mins before event1)
    # Note: ICS library uses Arrow objects or strict datetime. 
    # The SAMPLE_ICS has Z (UTC) times.
    
    now = datetime(2026, 1, 16, 9, 50, 0, tzinfo=timezone.utc)
    
    alarms = CalendarService.get_upcoming_alarms(calendar, now, lookahead_minutes=15)
    
    assert len(alarms) == 1
    assert alarms[0]["uid"] == "event1@example.com"
    assert alarms[0]["name"] == "Meeting in 10 mins"

def test_no_upcoming_alarms():
    calendar = CalendarService.parse_ics(SAMPLE_ICS)
    
    # Mock "now" as 2026-01-16 09:00:00 UTC (1 hour before event1)
    now = datetime(2026, 1, 16, 9, 0, 0, tzinfo=timezone.utc)
    
    alarms = CalendarService.get_upcoming_alarms(calendar, now, lookahead_minutes=15)
    
    assert len(alarms) == 0

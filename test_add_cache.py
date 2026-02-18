#!/usr/bin/env python3
"""Test _add_cache_entries directly."""

import sys

sys.path.insert(0, "/Users/philippegagne/Projets/espace-image")

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlmodel import select

from app.db.models import CalendarEventCache, CalendarSource
from app.db.session import get_session
from app.services.calendar_service import CalendarService

# Clear cache first
session = next(get_session())
session.exec(select(CalendarEventCache)).all()
for event in session.exec(select(CalendarEventCache)):
    session.delete(event)
session.commit()

print("✅ Cache cleared\n")

# Create test events dict (mimicking latest_by_uid output)
test_events = {
    "d5fcdcc3-e8b3-4c1a-a272-df2f6fff0257#2026-02-13T00:00:00+00:00": {
        "uid": "d5fcdcc3-e8b3-4c1a-a272-df2f6fff0257",
        "event_start": datetime(2026, 2, 13, 0, 0, 0, tzinfo=ZoneInfo("UTC")),
        "event_end": datetime(2026, 2, 14, 0, 0, 0, tzinfo=ZoneInfo("UTC")),
        "summary": "Congé 1 vendredi sur 2",
        "description": "",
        "location": "",
        "tzid": "America/Toronto",
        "trigger_time": None,
    },
    "d5fcdcc3-e8b3-4c1a-a272-df2f6fff0257#2026-02-27T00:00:00+00:00": {
        "uid": "d5fcdcc3-e8b3-4c1a-a272-df2f6fff0257",
        "event_start": datetime(2026, 2, 27, 0, 0, 0, tzinfo=ZoneInfo("UTC")),
        "event_end": datetime(2026, 2, 28, 0, 0, 0, tzinfo=ZoneInfo("UTC")),
        "summary": "Congé 1 vendredi sur 2",
        "description": "",
        "location": "",
        "tzid": "America/Toronto",
        "trigger_time": None,
    },
}

print(f"📝 Testing _add_cache_entries with {len(test_events)} events\n")

# Get calendar source
source = session.exec(select(CalendarSource).where(CalendarSource.id == 1)).first()

# Call _add_cache_entries
CalendarService._add_cache_entries(session, test_events, source)

session.commit()

# Check results
cached = session.exec(
    select(CalendarEventCache).where(CalendarEventCache.summary.like("%Congé%"))  # type: ignore
).all()

print(f"\n📊 Database now has {len(cached)} Congé event(s):\n")
for event in cached:
    print(f"  - UID: {event.uid[:60]}...")
    print(f"    Start: {event.event_start}")
    print()

session.close()

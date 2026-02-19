#!/usr/bin/env python3
"""Test extract_events_from_ics directly."""

import sys

sys.path.insert(0, "/Users/philippegagne/Projets/espace-image")

from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.calendar_service import CalendarService

# Read the ICS content
with open("famille.ics") as f:
    ics_content = f.read()

# Define window (February 2026)
window_start = datetime(2026, 2, 1, 0, 0, 0, tzinfo=ZoneInfo("UTC"))
window_end = datetime(2026, 3, 1, 0, 0, 0, tzinfo=ZoneInfo("UTC"))

print(f"📅 Extracting events from {window_start.date()} to {window_end.date()}\n")

# Call extract_events_from_ics
events = CalendarService.extract_events_from_ics(
    ics_content, source_id=1, window_start=window_start, window_end=window_end, fix_icloud=True
)

# Filter for Congé events
conge_events = [e for e in events if "Congé" in e["summary"]]

print(f"Found {len(conge_events)} 'Congé' event(s):\n")

for i, event in enumerate(conge_events, 1):
    print(f"Event {i}:")
    print(f"  Summary: {event['summary']}")
    print(f"  UID: {event['uid']}")
    print(f"  Start: {event['event_start']}")
    print(f"  End: {event['event_end']}")
    print()

# Now test _select_latest_by_uid
print("\n🔄 Testing _select_latest_by_uid...\n")
latest_by_uid = CalendarService._select_latest_by_uid(conge_events)

print(f"Result has {len(latest_by_uid)} entries:\n")
for uid, event in latest_by_uid.items():
    print(f"  Dict key (UID): {uid}")
    print(f"  Event[uid]: {event['uid']}")
    print(f"  Summary: {event['summary']}")
    print(f"  Start: {event['event_start']}")
    print()

#!/usr/bin/env python3
"""Fetch and analyze a different calendar URL."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.calendar_service import CalendarService


async def main():
    """Fetch and analyze calendar."""
    url = "webcal://p162-caldav.icloud.com/2/MTQzNzA5MjI2MTQzNzA5MnqUWUPKWoXGk9nW2qoKJdNBxqo1I3EDEunq90s7HMBKv2XRjhgv3SpvGdC1PmRznDZ_ffmaY1FR6wvO-GDQxlA"

    print("📅 Fetching calendar:")
    print(f"   {url}")
    print()
    print("   ⚠️  NOTE: This URL does NOT contain '/published/' - might include alarms!")
    print()

    ics_content = await CalendarService.fetch_ics(url)

    if not ics_content:
        print("❌ Failed to fetch calendar")
        return

    print(f"✅ Fetched {len(ics_content)} bytes")
    print()

    # Count events and VALARMs
    event_count = ics_content.count("BEGIN:VEVENT")
    valarm_count = ics_content.count("BEGIN:VALARM")

    print("📊 Summary:")
    print(f"   Total Events: {event_count}")
    print(f"   Total VALARMs: {valarm_count}")
    print()

    if valarm_count > 0:
        print(f"🎉 SUCCESS! This calendar HAS {valarm_count} VALARM components!")
        print()
        print("=" * 80)
        print("FIRST EVENT WITH VALARM:")
        print("=" * 80)

        # Find first VALARM
        valarm_idx = ics_content.find("BEGIN:VALARM")
        # Find the VEVENT containing it
        vevent_start = ics_content.rfind("BEGIN:VEVENT", 0, valarm_idx)
        vevent_end = ics_content.find("END:VEVENT", valarm_idx) + 11

        first_event = ics_content[vevent_start:vevent_end]
        print(first_event)
        print("=" * 80)
        print()

        # Show just the VALARM
        print("=" * 80)
        print("VALARM DETAILS:")
        print("=" * 80)
        valarm_end = ics_content.find("END:VALARM", valarm_idx) + 11
        print(ics_content[valarm_idx:valarm_end])
        print("=" * 80)

        # Save to file
        output_file = "/tmp/private_calendar.ics"
        with open(output_file, "w") as f:
            f.write(ics_content)
        print()
        print(f"✅ Full calendar saved to: {output_file}")

    else:
        print("❌ No VALARM components found in this calendar either")
        print()
        print("First event sample:")
        print("=" * 80)
        vevent_idx = ics_content.find("BEGIN:VEVENT")
        vevent_end = ics_content.find("END:VEVENT", vevent_idx) + 11
        print(ics_content[vevent_idx:vevent_end])
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

"""Simple CalDAV client adapter for fetching calendar ICS content.

This adapter is intentionally minimal: it supports a single account (from
env vars) and fetching a single calendar (exact URL/path match). It uses the
`caldav` library in a threadpool because that client is synchronous.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.config import (
    CALDAV_URL,
    CALDAV_USERNAME,
    CALDAV_PASSWORD,
    CALDAV_CALENDAR,
    CALDAV_SYNC_ENABLED,
)

logger = logging.getLogger(__name__)


async def fetch_caldav_calendar_ics() -> Optional[str]:
    """Fetch the configured CalDAV calendar as a combined ICS string.

    Returns None on failure or if CalDAV is not configured/enabled.
    """
    if not CALDAV_SYNC_ENABLED or not CALDAV_URL or not CALDAV_CALENDAR:
        logger.debug("CalDAV not configured or disabled; skipping CalDAV fetch")
        return None

    try:
        import caldav

        def _sync_fetch() -> Optional[str]:
            try:
                client = caldav.DAVClient(url=CALDAV_URL, username=CALDAV_USERNAME, password=CALDAV_PASSWORD)
                principal = client.principal()
                calendars = principal.calendars()
                # Find matching calendar by href or url fragment
                target = None
                for cal in calendars:
                    try:
                        href = getattr(cal, "url", None) or getattr(cal, "href", None)
                        if not href:
                            # Some caldav clients expose .url via properties
                            href = str(cal)
                        if CALDAV_CALENDAR in href or href in CALDAV_CALENDAR:
                            target = cal
                            break
                    except Exception:
                        continue
                if target is None:
                    logger.warning("CalDAV calendar matching '%s' not found", CALDAV_CALENDAR)
                    return None

                # Aggregate all events into a single VCALENDAR string
                items = []
                for ev in target.events():
                    try:
                        data = ev.data
                        if isinstance(data, bytes):
                            data = data.decode("utf-8", errors="ignore")
                        items.append(data)
                    except Exception:
                        continue

                if not items:
                    return None

                # If the events already contain full VCALENDAR blocks, join them
                # Otherwise, wrap VEVENT parts into a VCALENDAR envelope.
                combined = "\n".join(items)
                if "BEGIN:VCALENDAR" in combined.upper():
                    return combined
                return "BEGIN:VCALENDAR\n" + combined + "\nEND:VCALENDAR\n"
            except Exception as e:
                logger.exception("CalDAV fetch failed: %s", e)
                return None

        return await asyncio.to_thread(_sync_fetch)
    except ImportError:
        logger.warning("caldav library not installed; cannot fetch CalDAV calendars")
        return None

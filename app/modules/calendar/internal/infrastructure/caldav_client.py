"""Simple CalDAV client adapter for fetching calendar ICS content.

This adapter is intentionally minimal: it supports a single account (from
env vars) and fetching a single calendar (exact URL/path match). It uses the
`caldav` library in a threadpool because that client is synchronous.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field

import caldav

from app.config import (
    CALDAV_CALENDAR,
    CALDAV_CONNECT_TIMEOUT_SECONDS,
    CALDAV_MAX_RETRIES,
    CALDAV_PASSWORD,
    CALDAV_READ_TIMEOUT_SECONDS,
    CALDAV_SYNC_ENABLED,
    CALDAV_URL,
    CALDAV_USERNAME,
    CALDAV_VERIFY_SSL,
)

logger = logging.getLogger(__name__)


_ICAL_COMPONENT_RE = re.compile(
    r"BEGIN:(VEVENT|VTODO|VJOURNAL).*?END:\\1",
    re.IGNORECASE | re.DOTALL,
)


class CalDAVFetchError(RuntimeError):
    """Raised when authenticated CalDAV fetch fails unexpectedly."""


@dataclass(frozen=True)
class CalDAVElement:
    """Raw CalDAV object payload returned by the server."""

    uid: str
    href: str
    etag: str | None
    raw_ics: str


@dataclass(frozen=True)
class CalDAVFetchResult:
    """Result payload for CalDAV fetch including sync-token metadata."""

    content: str | None
    sync_token: str | None
    changed: bool
    elements: list[CalDAVElement] = field(default_factory=list)


def _normalize_calendar_url(url: str) -> str:
    """Normalize calendar URLs for resilient equality checks."""
    return url.strip().rstrip("/")


def _build_calendar_ics(items: list[str]) -> str | None:
    """Build a single VCALENDAR payload from fetched event payloads."""
    if not items:
        return None

    # Ensure we always return exactly one VCALENDAR block because
    # downstream parsers reject concatenated full calendars.
    components: list[str] = []
    for item in items:
        upper_item = item.upper()
        if "BEGIN:VCALENDAR" in upper_item:
            for match in _ICAL_COMPONENT_RE.finditer(item):
                components.append(match.group(0).strip())
            continue
        components.append(item.strip())

    if not components:
        return None

    return (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "PRODID:-//espace-image//CalDAV sync//EN\n"
        + "\n".join(components)
        + "\nEND:VCALENDAR\n"
    )


def _empty_calendar_ics() -> str:
    """Return a minimal valid empty VCALENDAR payload."""
    return "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//espace-image//CalDAV sync//EN\nEND:VCALENDAR\n"


async def fetch_caldav_calendar_ics_with_metadata(  # noqa: C901
    calendar_url: str | None = None,
    sync_token: str | None = None,
    fail_on_error: bool = False,
) -> CalDAVFetchResult:
    """Fetch one CalDAV calendar with sync-token aware metadata."""
    target_calendar = calendar_url or CALDAV_CALENDAR

    if not CALDAV_SYNC_ENABLED or not CALDAV_URL:
        logger.debug("CalDAV not configured or disabled; skipping CalDAV fetch")
        return CalDAVFetchResult(content=None, sync_token=sync_token, changed=False)
    if not target_calendar:
        logger.debug("CalDAV target calendar not configured; skipping CalDAV fetch")
        return CalDAVFetchResult(content=None, sync_token=sync_token, changed=False)

    try:
        timeout_seconds = max(CALDAV_CONNECT_TIMEOUT_SECONDS, CALDAV_READ_TIMEOUT_SECONDS)

        def _sync_fetch() -> CalDAVFetchResult:  # noqa: C901
            try:
                client = caldav.DAVClient(
                    url=CALDAV_URL,
                    username=CALDAV_USERNAME,
                    password=CALDAV_PASSWORD,
                    timeout=timeout_seconds,
                    ssl_verify_cert=CALDAV_VERIFY_SSL,
                )
                principal = client.principal()
                calendars = principal.calendars()
                normalized_target = _normalize_calendar_url(target_calendar)
                target = None
                for cal in calendars:
                    try:
                        href = getattr(cal, "url", None) or getattr(cal, "href", None)
                        if not href:
                            href = str(cal)
                        href_str = str(href)
                        normalized_href = _normalize_calendar_url(href_str)

                        if (
                            normalized_target == normalized_href
                            or normalized_target in normalized_href
                            or normalized_href in normalized_target
                        ):
                            target = cal
                            break
                    except Exception:
                        continue
                if target is None:
                    logger.warning("CalDAV calendar matching '%s' not found", target_calendar)
                    return CalDAVFetchResult(content=None, sync_token=sync_token, changed=False)

                # Ask server for changes since last token. If no changes, skip
                # full event download and reuse cached events in DB.
                sync_collection = target.get_objects_by_sync_token(sync_token=sync_token)
                new_sync_token = getattr(sync_collection, "sync_token", sync_token)
                changed = sync_token is None or len(sync_collection) > 0
                if not changed:
                    return CalDAVFetchResult(
                        content=None,
                        sync_token=new_sync_token,
                        changed=False,
                    )

                items = []
                elements: list[CalDAVElement] = []
                for ev in target.events():
                    try:
                        data = ev.data
                        if isinstance(data, bytes):
                            data = data.decode("utf-8", errors="ignore")
                        items.append(data)
                        href = str(getattr(ev, "url", None) or getattr(ev, "href", None) or "")
                        etag = getattr(ev, "etag", None)
                        uid = href.rstrip("/").split("/")[-1] or href or f"item-{len(elements) + 1}"
                        elements.append(
                            CalDAVElement(
                                uid=uid,
                                href=href,
                                etag=str(etag) if etag is not None else None,
                                raw_ics=data,
                            )
                        )
                    except Exception:
                        continue

                content = _build_calendar_ics(items) or _empty_calendar_ics()
                return CalDAVFetchResult(
                    content=content,
                    sync_token=new_sync_token,
                    changed=True,
                    elements=elements,
                )
            except Exception as e:
                raise CalDAVFetchError(str(e)) from e

        retries = max(1, CALDAV_MAX_RETRIES)
        for attempt in range(1, retries + 1):
            try:
                return await asyncio.to_thread(_sync_fetch)
            except CalDAVFetchError as exc:
                logger.warning(
                    "CalDAV authenticated fetch attempt %d/%d failed: %s",
                    attempt,
                    retries,
                    exc,
                )
                if attempt == retries:
                    if fail_on_error:
                        raise
                    return CalDAVFetchResult(content=None, sync_token=sync_token, changed=False)
                await asyncio.sleep(min(2 ** (attempt - 1), 8))
        return CalDAVFetchResult(content=None, sync_token=sync_token, changed=False)
    except ImportError:
        logger.warning("caldav library not installed; cannot fetch CalDAV calendars")
        return CalDAVFetchResult(content=None, sync_token=sync_token, changed=False)


async def fetch_caldav_calendar_ics(
    calendar_url: str | None = None,
    sync_token: str | None = None,
    fail_on_error: bool = False,
) -> str | None:
    """Fetch the configured CalDAV calendar as a combined ICS string.

    Returns None on failure or if CalDAV is not configured/enabled.
    """
    result = await fetch_caldav_calendar_ics_with_metadata(
        calendar_url=calendar_url,
        sync_token=sync_token,
        fail_on_error=fail_on_error,
    )
    return result.content

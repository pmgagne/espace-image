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
from typing import Any, cast
from urllib.parse import urlparse

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
    fetch_succeeded: bool = True
    elements: list[CalDAVElement] = field(default_factory=list)


def _normalize_calendar_url(url: str) -> str:
    """Normalize calendar URLs for resilient equality checks."""
    return url.strip().rstrip("/")


def _same_calendar_url(left: str, right: str) -> bool:
    """Return True when two URLs refer to the same CalDAV calendar."""
    normalized_left = _normalize_calendar_url(left)
    normalized_right = _normalize_calendar_url(right)
    if not normalized_left or not normalized_right:
        return False
    return (
        normalized_left == normalized_right
        or normalized_left in normalized_right
        or normalized_right in normalized_left
    )


def _find_matching_calendar(calendars: list[Any], target_calendar: str) -> Any | None:
    """Find one discovered calendar matching the requested URL/path."""
    normalized_target = _normalize_calendar_url(target_calendar)
    target_path = urlparse(normalized_target).path.rstrip("/")

    for calendar in calendars:
        try:
            href = getattr(calendar, "url", None) or getattr(calendar, "href", None)
            href_str = str(href or calendar)
            normalized_href = _normalize_calendar_url(href_str)
            href_path = urlparse(normalized_href).path.rstrip("/")
            if _same_calendar_url(normalized_target, normalized_href):
                return calendar
            if target_path and href_path and target_path == href_path:
                return calendar
        except Exception:
            continue

    return None


def _empty_fetch_result(sync_token: str | None, fetch_succeeded: bool = False) -> CalDAVFetchResult:
    """Return an empty CalDAV fetch result for failed or skipped fetches."""
    return CalDAVFetchResult(
        content=None,
        sync_token=sync_token,
        changed=False,
        fetch_succeeded=fetch_succeeded,
    )


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
        "PRODID:-//espace-image//CalDAV sync//EN\n" + "\n".join(components) + "\nEND:VCALENDAR\n"
    )


def _empty_calendar_ics() -> str:
    """Return a minimal valid empty VCALENDAR payload."""
    return "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//espace-image//CalDAV sync//EN\nEND:VCALENDAR\n"


def _fetch_calendar_with_metadata(calendar: Any, sync_token: str | None) -> CalDAVFetchResult:
    """Fetch one discovered CalDAV calendar using an existing DAV context."""
    sync_collection = calendar.get_objects_by_sync_token(sync_token=sync_token)
    new_sync_token = getattr(sync_collection, "sync_token", sync_token)
    changed = sync_token is None or len(sync_collection) > 0
    if not changed:
        return CalDAVFetchResult(
            content=None,
            sync_token=new_sync_token,
            changed=False,
            fetch_succeeded=True,
        )

    items: list[str] = []
    elements: list[CalDAVElement] = []
    for event in calendar.events():
        try:
            data = event.data
            if isinstance(data, bytes):
                data = data.decode("utf-8", errors="ignore")
            items.append(data)
            href = str(getattr(event, "url", None) or getattr(event, "href", None) or "")
            etag = getattr(event, "etag", None)
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

    return CalDAVFetchResult(
        content=_build_calendar_ics(items) or _empty_calendar_ics(),
        sync_token=new_sync_token,
        changed=True,
        fetch_succeeded=True,
        elements=elements,
    )


async def fetch_caldav_calendars_with_metadata(
    requests: list[tuple[str, str | None]],
    fail_on_error: bool = False,
) -> dict[str, CalDAVFetchResult]:
    """Fetch multiple CalDAV calendars while reusing one DAV client/principal context."""
    if not CALDAV_SYNC_ENABLED or not CALDAV_URL or not requests:
        return {
            calendar_url: _empty_fetch_result(sync_token, fetch_succeeded=False)
            for calendar_url, sync_token in requests
        }

    try:
        timeout_seconds = max(CALDAV_CONNECT_TIMEOUT_SECONDS, CALDAV_READ_TIMEOUT_SECONDS)

        def _sync_fetch_many() -> dict[str, CalDAVFetchResult]:
            try:
                dav_client_cls = cast(Any, caldav.DAVClient)
                client = dav_client_cls(
                    url=CALDAV_URL,
                    username=CALDAV_USERNAME,
                    password=CALDAV_PASSWORD,
                    timeout=timeout_seconds,
                    ssl_verify_cert=CALDAV_VERIFY_SSL,
                )
                principal = client.principal()
                calendars = list(principal.calendars())
                results: dict[str, CalDAVFetchResult] = {}

                for calendar_url, sync_token in requests:
                    target = _find_matching_calendar(calendars, calendar_url)
                    if target is None:
                        logger.warning("CalDAV calendar matching '%s' not found", calendar_url)
                        results[calendar_url] = _empty_fetch_result(
                            sync_token,
                            fetch_succeeded=False,
                        )
                        continue

                    try:
                        results[calendar_url] = _fetch_calendar_with_metadata(target, sync_token)
                    except Exception as exc:
                        logger.warning("CalDAV fetch failed for '%s': %s", calendar_url, exc)
                        results[calendar_url] = _empty_fetch_result(
                            sync_token,
                            fetch_succeeded=False,
                        )

                return results
            except Exception as exc:
                raise CalDAVFetchError(str(exc)) from exc

        retries = max(1, CALDAV_MAX_RETRIES)
        for attempt in range(1, retries + 1):
            try:
                return await asyncio.to_thread(_sync_fetch_many)
            except CalDAVFetchError as exc:
                logger.warning(
                    "CalDAV authenticated batch fetch attempt %d/%d failed: %s",
                    attempt,
                    retries,
                    exc,
                )
                if attempt == retries:
                    if fail_on_error:
                        raise
                    return {
                        calendar_url: _empty_fetch_result(sync_token, fetch_succeeded=False)
                        for calendar_url, sync_token in requests
                    }
                await asyncio.sleep(min(2 ** (attempt - 1), 8))
        return {
            calendar_url: _empty_fetch_result(sync_token, fetch_succeeded=False)
            for calendar_url, sync_token in requests
        }
    except ImportError:
        logger.warning("caldav library not installed; cannot fetch CalDAV calendars")
        return {
            calendar_url: _empty_fetch_result(sync_token, fetch_succeeded=False)
            for calendar_url, sync_token in requests
        }


async def fetch_caldav_calendar_ics_with_metadata(
    calendar_url: str | None = None,
    sync_token: str | None = None,
    fail_on_error: bool = False,
) -> CalDAVFetchResult:
    """Fetch one CalDAV calendar with sync-token aware metadata."""
    target_calendar = calendar_url or CALDAV_CALENDAR

    if not CALDAV_SYNC_ENABLED or not CALDAV_URL:
        logger.debug("CalDAV not configured or disabled; skipping CalDAV fetch")
        return _empty_fetch_result(sync_token, fetch_succeeded=False)
    if not target_calendar:
        logger.debug("CalDAV target calendar not configured; skipping CalDAV fetch")
        return _empty_fetch_result(sync_token, fetch_succeeded=False)

    results = await fetch_caldav_calendars_with_metadata(
        [(target_calendar, sync_token)],
        fail_on_error=fail_on_error,
    )
    return results.get(target_calendar, _empty_fetch_result(sync_token, fetch_succeeded=False))


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

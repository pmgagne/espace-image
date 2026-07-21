"""Simple CalDAV client adapter for fetching calendar ICS content.

This adapter is intentionally minimal: it supports a single account (from
env vars) and fetching a single calendar (exact URL/path match). It uses the
`caldav` library in a threadpool because that client is synchronous.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, cast
from urllib.parse import urlparse

from app.config import (
    CALDAV_CALENDAR,
    CALDAV_CONNECT_TIMEOUT_SECONDS,
    CALDAV_DISABLE_HTTP3,
    CALDAV_MAX_RETRIES,
    CALDAV_PASSWORD,
    CALDAV_READ_TIMEOUT_SECONDS,
    CALDAV_SYNC_ENABLED,
    CALDAV_URL,
    CALDAV_USERNAME,
    CALDAV_VERIFY_SSL,
)

# If the operator has requested HTTP/3 disabling, set environment hints early
# (before importing HTTP client libraries) so downstream libraries pick them up.
if CALDAV_DISABLE_HTTP3:
    # Best-effort toggle for various HTTP stacks
    os.environ.setdefault("HTTPX_DISABLE_HTTP3", "1")
    os.environ.setdefault("AIOHTTP_NO_HTTP3", "1")
    os.environ.setdefault("DISABLE_HTTP3", "1")

import caldav

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


def _path_segments(path: str) -> list[str]:
    """Split a URL path into non-empty segments."""
    return [segment for segment in path.split("/") if segment]


def _is_segment_suffix(left_segments: list[str], right_segments: list[str]) -> bool:
    """Return True when one segment list is a trailing sublist of the other.

    Restricted to whole path segments so a bare calendar name or partial
    path (e.g. CALDAV_CALENDAR="home") matches a full server href
    (".../calendars/home") without incorrectly matching
    ".../calendars/home-work" — that would require an exact segment
    "home-work" == "home", which fails.
    """
    if not left_segments or not right_segments:
        return False
    shorter, longer = (
        (left_segments, right_segments)
        if len(left_segments) <= len(right_segments)
        else (right_segments, left_segments)
    )
    return longer[len(longer) - len(shorter) :] == shorter


def _same_calendar_url(left: str, right: str) -> bool:
    """Return True when two URLs refer to the same CalDAV calendar.

    Compares full normalized URLs first, then path equality, then falls back
    to a segment-boundary suffix match so a configured partial path or
    calendar name (CALDAV_CALENDAR="personal" or "user/personal") still
    matches a full server href. Substring containment is intentionally
    avoided — it would incorrectly match /calendars/home against
    /calendars/home-work; segment-boundary comparison does not.
    """
    normalized_left = _normalize_calendar_url(left)
    normalized_right = _normalize_calendar_url(right)
    if not normalized_left or not normalized_right:
        return False
    if normalized_left == normalized_right:
        return True
    left_path = urlparse(normalized_left).path.rstrip("/")
    right_path = urlparse(normalized_right).path.rstrip("/")
    if left_path and right_path and left_path == right_path:
        return True
    return _is_segment_suffix(_path_segments(left_path), _path_segments(right_path))


def _find_matching_calendar(calendars: list[Any], target_calendar: str) -> Any | None:
    """Find one discovered calendar matching the requested URL/path."""
    normalized_target = _normalize_calendar_url(target_calendar)

    for calendar in calendars:
        try:
            href = getattr(calendar, "url", None) or getattr(calendar, "href", None)
            href_str = str(href or calendar)
            normalized_href = _normalize_calendar_url(href_str)
            if _same_calendar_url(normalized_target, normalized_href):
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


def _sync_fetch_many_impl(
    requests: list[tuple[str, str | None]], timeout_seconds: int
) -> dict[str, CalDAVFetchResult]:
    """Synchronous implementation that performs authenticated DAV batch fetches.

    Extracted to a top-level function to keep the async wrapper simple and
    reduce function complexity for linters.
    """
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

        # If requested, try to disable HTTP/3 negotiation by setting common
        # environment variables used by httpx/aiohttp/httpcore-based clients.
        # This is a best-effort toggle to work around servers that advertise
        # Alt-Svc/HTTP/3 support but are incompatible with the client stack.
        if CALDAV_DISABLE_HTTP3:
            import os

            logger.info("CALDAV_DISABLE_HTTP3 set: disabling HTTP/3 negotiation for CalDAV client")
            # httpx/httpcore hint
            os.environ.setdefault("HTTPX_DISABLE_HTTP3", "1")
            # aiohttp/alpn hint (not standardized; some builds read this)
            os.environ.setdefault("AIOHTTP_NO_HTTP3", "1")
            # generic hint for other potential stacks
            os.environ.setdefault("DISABLE_HTTP3", "1")

        retries = max(1, CALDAV_MAX_RETRIES)
        for attempt in range(1, retries + 1):
            try:
                return await asyncio.to_thread(_sync_fetch_many_impl, requests, timeout_seconds)
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

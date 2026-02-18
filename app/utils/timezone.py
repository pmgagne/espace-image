import logging
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


def ensure_utc_aware(dt: datetime) -> datetime:
    """
    Ensure a datetime is timezone-aware and in UTC.

    Args:
        dt (datetime): Datetime instance (naive or aware).

    Returns:
        datetime: Timezone-aware datetime in UTC.

    Raises:
        TypeError: If dt is not a datetime instance or is None.
    """
    if dt is None:
        raise TypeError("dt must be a datetime, got None")
    if not isinstance(dt, datetime):
        raise TypeError(f"Expected datetime, got {type(dt)}")

    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)

    # Normalize to UTC
    try:
        return dt.astimezone(UTC)
    except Exception as e:
        logger.warning("Failed to astimezone datetime to UTC: %s", e)
        return dt.replace(tzinfo=UTC)


def ensure_aware(dt: datetime, tzname: str | None = None) -> datetime:
    """
    Ensure a datetime is timezone-aware without converting its wall-clock time.

    If `dt` is naive, attach the provided `tzname` (IANA) or system local
    timezone. If `dt` is already aware, it is returned unchanged.
    """
    if dt is None:
        raise TypeError("dt must be a datetime, got None")
    if not isinstance(dt, datetime):
        raise TypeError(f"Expected datetime, got {type(dt)}")

    if dt.tzinfo is not None:
        return dt

    if tzname:
        try:
            return dt.replace(tzinfo=ZoneInfo(tzname))
        except Exception:
            logger.debug("Invalid tzname passed to ensure_aware: %s", tzname)

    # Fallback: attach system local tz
    try:
        return dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
    except Exception:
        return dt.replace(tzinfo=UTC)


def to_utc(dt: datetime) -> datetime:
    """
    Convert a datetime to UTC. If datetime is naive, assume it's in UTC.
    Use this when you explicitly want a UTC-normalized value.
    """
    if dt is None:
        raise TypeError("dt must be a datetime, got None")
    if not isinstance(dt, datetime):
        raise TypeError(f"Expected datetime, got {type(dt)}")

    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    try:
        return dt.astimezone(UTC)
    except Exception:
        return dt.replace(tzinfo=UTC)


def normalize_datetime(val: datetime | date | None) -> datetime | None:
    """
    Normalize a date or datetime-like value to an aware UTC datetime.

    Accepts datetime or date objects. Returns UTC-aware datetime.

    Args:
        val: A datetime or date-like object.

    Returns:
        datetime | None: UTC-aware datetime, or None if input is None.

    Raises:
        TypeError: For unsupported types.
    """
    if val is None:
        return None

    if isinstance(val, datetime):
        return ensure_utc_aware(val)

    # Assume it's a date-like object (from ical components)
    try:
        # create a datetime at midnight of that date in UTC
        return datetime.combine(val, time.min, tzinfo=UTC)
    except Exception as err:
        raise TypeError(f"Cannot normalize value of type {type(val)} to datetime") from err


def get_local_timezone_name() -> str:
    """
    Return a human-friendly name for the system's local timezone.

    Tries to return an IANA/ZoneInfo key if available, otherwise falls back
    to the tzname abbreviation.

    Returns:
        str: The local timezone name or abbreviation.
    """
    try:
        tz = datetime.now().astimezone().tzinfo
        if tz is None:
            return "UTC"
        # ZoneInfo has attribute 'key' on Python 3.9+ when created via ZoneInfo
        name = getattr(tz, "key", None) or getattr(tz, "zone", None)
        if name:
            return str(name)
        return tz.tzname(None) or "UTC"
    except Exception:
        logger.exception("Unable to determine local timezone name")
        return "UTC"


def format_datetime_in_local(dt: datetime, fmt: str | None = None) -> str:
    """
    Format a datetime in the system local timezone.

    If `dt` is naive it will be treated as UTC. Returns a human-friendly
    representation including the timezone abbreviation.

    Args:
        dt (datetime): The datetime to format.
        fmt (str | None): Optional format string.

    Returns:
        str: Formatted datetime string in local timezone.
    """
    if dt is None:
        return ""
    try:
        if fmt is None:
            fmt = "%Y-%m-%d %H:%M:%S %Z"
        # If naive, assume UTC (stored values are UTC)
        if getattr(dt, "tzinfo", None) is None:
            from datetime import UTC

            dt = dt.replace(tzinfo=UTC)

        local_tz = datetime.now().astimezone().tzinfo
        local_dt = dt.astimezone(local_tz)
        return local_dt.strftime(fmt)
    except Exception:
        logger.exception("Failed to format datetime in local timezone")
        try:
            return str(dt)
        except Exception:
            return ""


def datetime_to_iso_with_tz(dt: datetime, event_tz: str | None = None) -> str:
    """
    Convert a UTC datetime to ISO 8601 format with the original event timezone offset.

    All datetimes in the database are stored in UTC. This function converts them
    to ISO 8601 format with the timezone offset calculated from the original event timezone.

    Args:
        dt (datetime): A UTC datetime (expected to be timezone-aware in UTC).
        event_tz (str | None): IANA timezone name of the original event (e.g., "America/Toronto").
                               If provided, the ISO string will include the offset from that timezone.
                               If None, returns ISO 8601 UTC format.

    Returns:
        str: ISO 8601 formatted datetime string with timezone offset or Z for UTC.

    Example:
        >>> dt = datetime(2026, 2, 17, 15, 0, 0, tzinfo=UTC)  # 3 PM UTC
        >>> datetime_to_iso_with_tz(dt, "America/Toronto")
        '2026-02-17T10:00:00-05:00'  # 10 AM Toronto time
    """
    if dt is None:
        return ""

    # Ensure dt is UTC-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    # If no event timezone specified, return ISO format in UTC
    if not event_tz:
        return dt.isoformat()

    try:
        # Convert UTC datetime to the original event timezone
        event_tz_info = ZoneInfo(event_tz)
        local_dt = dt.astimezone(event_tz_info)
        # Return ISO format with timezone offset
        return local_dt.isoformat()
    except Exception as e:
        logger.warning("Failed to convert datetime to timezone %s: %s", event_tz, e)
        # Fallback to UTC ISO format
        return dt.isoformat()

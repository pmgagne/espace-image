import logging
from datetime import UTC, datetime, time

logger = logging.getLogger(__name__)


def ensure_utc_aware(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware and in UTC.

    Args:
        dt: datetime instance (naive or aware)

    Returns:
        datetime: timezone-aware datetime in UTC

    Raises:
        TypeError: if dt is not a datetime instance
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


def normalize_datetime(val):
    """Normalize a date or datetime-like value to an aware UTC datetime.

    Accepts datetime or date objects. Returns UTC-aware datetime.
    Raises TypeError for unsupported types.
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
    """Return a human-friendly name for the system's local timezone.

    Tries to return an IANA/ZoneInfo key if available, otherwise falls back
    to the tzname abbreviation.
    """
    try:
        tz = datetime.now().astimezone().tzinfo
        # ZoneInfo has attribute 'key' on Python 3.9+ when created via ZoneInfo
        name = getattr(tz, "key", None) or getattr(tz, "zone", None)
        if name:
            return str(name)
        return tz.tzname(None) or "UTC"
    except Exception:
        logger.exception("Unable to determine local timezone name")
        return "UTC"


def format_datetime_in_local(dt, fmt: str | None = None) -> str:
    """Format a datetime in the system local timezone.

    If `dt` is naive it will be treated as UTC. Returns a human-friendly
    representation including the timezone abbreviation.
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

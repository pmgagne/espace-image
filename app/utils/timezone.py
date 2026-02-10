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
    except Exception:
        raise TypeError(f"Cannot normalize value of type {type(val)} to datetime")

"""Calendar module exceptions."""


class CalendarModuleError(Exception):
    """Base exception for calendar module errors."""

    pass


class CalendarSyncError(CalendarModuleError):
    """Raised when calendar synchronization fails."""

    pass


class CalendarSourceNotFoundError(CalendarModuleError):
    """Raised when a calendar source is not found."""

    pass

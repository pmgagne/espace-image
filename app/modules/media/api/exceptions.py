"""Media module exceptions."""


class MediaModuleError(Exception):
    """Base exception for media module public API."""


class MediaValidationError(MediaModuleError):
    """Raised when media validation fails for uploads."""

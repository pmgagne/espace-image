"""Settings module exceptions."""


class SettingsModuleError(Exception):
    """Base exception for settings module public API."""


class PresetNotFoundError(SettingsModuleError):
    """Raised when a preset cannot be found."""

"""Data contracts for settings module."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PresetDTO:
    """Data transfer object for a preset."""

    id: int
    name: str
    photo_count: int = 0


@dataclass(frozen=True)
class AppSettingsDTO:
    """Data transfer object for application settings."""

    active_preset_id: int | None
    weather_latitude: float | None
    weather_longitude: float | None
    slideshow_duration: int


@dataclass(frozen=True)
class SettingsFormDTO:
    """Data transfer object for settings form rendering and preview state."""

    active_preset_id: int | None
    weather_latitude: float | None
    weather_longitude: float | None
    slideshow_duration: int

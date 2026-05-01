"""Data contracts for settings module."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PresetDTO:
    """Data transfer object for a preset."""

    id: int
    name: str


@dataclass(frozen=True)
class AppSettingsDTO:
    """Data transfer object for application settings."""

    active_preset_id: int | None
    weather_latitude: float | None
    weather_longitude: float | None
    slideshow_duration: int
    default_alarm_for_all_events: bool

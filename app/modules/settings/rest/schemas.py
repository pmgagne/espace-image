"""REST-only request models for settings endpoints."""

from pydantic import BaseModel


class ActivePresetRequest(BaseModel):
    """Request payload for changing the active preset."""

    active_preset_id: int | None


class SlideshowDurationRequest(BaseModel):
    """Request payload for changing slideshow duration."""

    slideshow_duration: int


class WeatherLocationRequest(BaseModel):
    """Request payload for changing weather coordinates."""

    latitude: float | None
    longitude: float | None

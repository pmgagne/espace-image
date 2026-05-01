"""Public interfaces for the weather module."""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class WeatherData:
    """Normalized weather payload used by web templates and endpoints."""

    temp: int | str
    condition: str
    location: str


@dataclass
class WeatherLocationResult:
    """Normalized geocoding result payload."""

    lat: float
    lon: float
    name: str


class IWeatherService(Protocol):
    """Public interface for weather and geocoding operations."""

    async def get_current_weather(self, lat: float, lon: float) -> WeatherData:
        """Fetch the current weather for coordinates."""
        ...

    async def geocode_location(self, query: str) -> WeatherLocationResult | None:
        """Resolve a location name to coordinates."""
        ...

    async def reverse_geocode(self, lat: float, lon: float) -> str | None:
        """Resolve coordinates to a human-readable location name."""
        ...


def get_weather_service() -> IWeatherService:
    """Dependency injection token for the weather service."""
    raise NotImplementedError("Weather service not initialized")

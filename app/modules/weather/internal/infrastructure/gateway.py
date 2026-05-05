"""Weather gateway adapter for provider API calls."""

from typing import Any

from app.modules.weather.api.gateway import IWeatherGateway
from app.modules.weather.internal.infrastructure.weather_api import WeatherService


class WeatherGateway(IWeatherGateway):
    """Weather gateway implementing `IWeatherGateway`.

    Delegates provider calls to the provider-backed `WeatherService`
    implementation and returns normalized payloads expected by callers.
    """

    async def get_current_weather(self, lat: float, lon: float) -> dict[str, Any]:
        """Fetch normalized weather payload from provider."""
        return await WeatherService.get_current_weather(lat, lon)

    async def geocode_location(self, query: str) -> dict[str, Any] | None:
        """Geocode a location query into coordinates."""
        return await WeatherService.geocode_location(query)

    async def reverse_geocode(self, lat: float, lon: float) -> str | None:
        """Reverse geocode coordinates into label."""
        return await WeatherService.reverse_geocode(lat, lon)

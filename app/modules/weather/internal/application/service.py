"""Weather module service implementation."""

from app.modules.weather.api.interfaces import IWeatherService, WeatherData, WeatherLocationResult
from app.modules.weather.internal.infrastructure.weather_api import (
    WeatherService as LegacyWeatherService,
)


class WeatherModuleService(IWeatherService):
    """Adapter service that preserves existing weather behavior during migration."""

    async def get_current_weather(self, lat: float, lon: float) -> WeatherData:
        """Return normalized weather data for the given coordinates."""
        data = await LegacyWeatherService.get_current_weather(lat, lon)
        return WeatherData(
            temp=data.get("temp", "--"),
            condition=data.get("condition", "Service Error"),
            location=data.get("location", "Unavailable"),
        )

    async def geocode_location(self, query: str) -> WeatherLocationResult | None:
        """Return normalized geocoding data for a user query."""
        data = await LegacyWeatherService.geocode_location(query)
        if data is None:
            return None
        return WeatherLocationResult(
            lat=float(data["lat"]),
            lon=float(data["lon"]),
            name=str(data["name"]),
        )


def create_weather_service() -> IWeatherService:
    """Factory that returns the weather service implementation."""
    return WeatherModuleService()

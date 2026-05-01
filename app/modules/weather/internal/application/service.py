"""Weather module service implementation."""

from app.db.session_factory import SessionFactory
from app.modules.weather.api.interfaces import (
    IWeatherService,
    WeatherData,
    WeatherLocationResult,
)
from app.modules.weather.internal.infrastructure.weather_api import (
    WeatherService as LegacyWeatherService,
)


class WeatherModuleService(IWeatherService):
    """Adapter service that preserves existing weather behavior during migration."""

    def __init__(self, session_factory: SessionFactory) -> None:
        """Initialize weather service with session factory dependency."""
        self._session_factory = session_factory

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

    async def reverse_geocode(self, lat: float, lon: float) -> str | None:
        """Return a human-readable location name for coordinates."""
        return await LegacyWeatherService.reverse_geocode(lat, lon)

    async def get_weather_html(self, lat: float | None, lon: float | None) -> str:
        """
        Get rendered HTML for weather component.

        Returns empty HTML fragment if no coordinates provided.
        Otherwise returns rendered weather widget with current conditions.
        """
        from app.template_config import templates

        # No location configured
        if lat is None or lon is None:
            tpl = templates.env.get_template("partials/weather.html")
            return tpl.render(has_location=False)

        # Fetch and render weather
        weather_data = await self.get_current_weather(lat, lon)
        weather = {
            "temp": weather_data.temp,
            "condition": weather_data.condition,
            "location": weather_data.location,
        }

        tpl = templates.env.get_template("partials/weather.html")
        return tpl.render(has_location=True, weather=weather)


def create_weather_service(session_factory: SessionFactory) -> IWeatherService:
    """Factory that returns the weather service implementation."""
    return WeatherModuleService(session_factory)

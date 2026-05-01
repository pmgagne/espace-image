"""Weather module service implementation."""

from app.db.session_factory import SessionFactory
from app.modules.weather.api.gateway import IWeatherGateway
from app.modules.weather.api.interfaces import (
    IWeatherService,
    WeatherData,
    WeatherLocationResult,
)
from app.modules.weather.api.presenters import IWeatherPresenter


class WeatherModuleService(IWeatherService):
    """Adapter service that preserves existing weather behavior during migration."""

    def __init__(
        self,
        session_factory: SessionFactory,
        gateway: IWeatherGateway,
        presenter: IWeatherPresenter,
    ) -> None:
        """Initialize weather service with session factory, gateway, and presenter."""
        self._session_factory = session_factory
        self._gateway = gateway
        self._presenter = presenter

    async def get_current_weather(self, lat: float, lon: float) -> WeatherData:
        """Return normalized weather data for the given coordinates."""
        data = await self._gateway.get_current_weather(lat, lon)
        return WeatherData(
            temp=data.get("temp", "--"),
            condition=data.get("condition", "Service Error"),
            location=data.get("location", "Unavailable"),
        )

    async def geocode_location(self, query: str) -> WeatherLocationResult | None:
        """Return normalized geocoding data for a user query."""
        data = await self._gateway.geocode_location(query)
        if data is None:
            return None
        return WeatherLocationResult(
            lat=float(data["lat"]),
            lon=float(data["lon"]),
            name=str(data["name"]),
        )

    async def reverse_geocode(self, lat: float, lon: float) -> str | None:
        """Return a human-readable location name for coordinates."""
        return await self._gateway.reverse_geocode(lat, lon)

    async def get_weather_html(self, lat: float | None, lon: float | None) -> str:
        """
        Get rendered HTML for weather component.

        Returns empty HTML fragment if no coordinates provided.
        Otherwise returns rendered weather widget with current conditions.
        """
        # No location configured
        if lat is None or lon is None:
            return self._presenter.render_weather_html(has_location=False)

        # Fetch and render weather
        weather_data = await self.get_current_weather(lat, lon)
        weather = {
            "temp": weather_data.temp,
            "condition": weather_data.condition,
            "location": weather_data.location,
        }

        return self._presenter.render_weather_html(has_location=True, weather=weather)

    async def get_weather_oob_html(self, lat: float | None, lon: float | None) -> str:
        """Return out-of-band weather wrapper fragment for index refresh polling."""
        if lat is None or lon is None:
            return ""
        weather_html = await self.get_weather_html(lat, lon)
        if not weather_html:
            return ""
        return f'<div hx-swap-oob="innerHTML:#weather-wrapper">{weather_html}</div>'

    async def get_location_name(self, lat: float | None, lon: float | None) -> str:
        """Return a best-effort location label for settings UI coordinates."""
        if lat is None or lon is None:
            return ""
        try:
            return await self.reverse_geocode(lat, lon) or ""
        except Exception:
            return ""

    async def geocode_for_settings(self, query: str) -> tuple[float | None, float | None, str]:
        """Geocode settings query and return preview coordinates plus display name."""
        result = await self.geocode_location(query)
        if result is None:
            return None, None, "Location not found"
        return result.lat, result.lon, result.name


def create_weather_service(
    session_factory: SessionFactory,
    gateway: IWeatherGateway,
    presenter: IWeatherPresenter,
) -> IWeatherService:
    """Factory that returns the weather service implementation."""
    return WeatherModuleService(session_factory, gateway, presenter)

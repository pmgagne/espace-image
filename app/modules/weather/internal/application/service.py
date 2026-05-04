"""Weather module service implementation."""

from app.db.session_factory import SessionFactory
from app.modules.weather.api.gateway import IWeatherGateway
from app.modules.weather.api.interfaces import (
    IWeatherService,
    WeatherData,
    WeatherLocationResult,
)


class WeatherModuleService(IWeatherService):
    """Weather service implementing `IWeatherService`.

    Adapts gateway/provider results into normalized `WeatherData` and
    renders HTML fragments via the provided presenter.
    """

    def __init__(
        self,
        session_factory: SessionFactory,
        gateway: IWeatherGateway,
    ) -> None:
        """Initialize weather service with session factory and gateway dependencies."""
        self._session_factory = session_factory
        self._gateway = gateway

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
) -> IWeatherService:
    """Factory that returns the weather service implementation."""
    return WeatherModuleService(session_factory, gateway)

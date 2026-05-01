"""Gateway port for weather external integrations."""

from typing import Any, Protocol


class IWeatherGateway(Protocol):
    """External API gateway for weather and geocoding operations."""

    async def get_current_weather(self, lat: float, lon: float) -> dict[str, Any]:
        """Fetch normalized weather payload from provider."""
        ...

    async def geocode_location(self, query: str) -> dict[str, Any] | None:
        """Geocode a location query into coordinates."""
        ...

    async def reverse_geocode(self, lat: float, lon: float) -> str | None:
        """Reverse geocode coordinates into label."""
        ...

import logging
from typing import Any, ClassVar

import httpx

logger = logging.getLogger(__name__)


class WeatherService:
    """
    Service for fetching current weather and geocoding locations using
    Open-Meteo APIs.
    """

    # WMO Weather interpretation codes (WW)
    # https://open-meteo.com/en/docs
    WMO_CODES: ClassVar[dict[int, str]] = {
        0: "Ciel dégagé",
        1: "Principalement dégagé",
        2: "Partiellement nuageux",
        3: "Couvert",
        45: "Brouillard",
        48: "Brouillard givrant",
        51: "Bruine légère",
        53: "Bruine modérée",
        55: "Bruine dense",
        61: "Pluie légère",
        63: "Pluie modérée",
        65: "Pluie forte",
        71: "Chute de neige légère",
        73: "Chute de neige modérée",
        75: "Chute de neige forte",
        77: "Grains de neige",
        80: "Averses de pluie légères",
        81: "Averses de pluie modérées",
        82: "Averses de pluie violentes",
        85: "Averses de neige légères",
        86: "Averses de neige fortes",
        95: "Orage",
        96: "Orage avec grêle légère",
        99: "Orage avec grêle forte",
    }

    @staticmethod
    async def get_current_weather(lat: float, lon: float) -> dict[str, Any]:
        """
        Fetch current weather from Open-Meteo.

        Args:
            lat (float): Latitude.
            lon (float): Longitude.

        Returns:
            dict: Weather data with keys 'temp', 'condition', and 'location'.
        """
        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params: dict[str, float | str | int] = {
                "latitude": lat,
                "longitude": lon,
                "current_weather": 1,
            }
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=5.0)
                response.raise_for_status()
                data = response.json()

                current = data.get("current_weather", {})
                temp = current.get("temperature")
                code = current.get("weathercode")

                condition = WeatherService.WMO_CODES.get(code, "Inconnu")

                # Defensive handling: the API may omit `temperature` in
                # error cases.
                if temp is None:
                    temp_val: Any = "--"
                else:
                    try:
                        temp_val = round(temp)
                    except Exception:
                        temp_val = "--"

                location = f"{lat:.2f}, {lon:.2f}"
                return {
                    "temp": temp_val,
                    "condition": condition,
                    "location": location,
                }
        except Exception:
            logger.exception(
                "Weather API error while fetching current weather",
            )
            return {
                "temp": "--",
                "condition": "Service Error",
                "location": "Unavailable",
            }

    @staticmethod
    async def geocode_location(query: str) -> dict[str, Any] | None:
        """
        Search for a location name using Open-Meteo Geocoding API.

        Args:
            query (str): Location name to search for.

        Returns:
            dict[str, Any] | None: {'lat': float, 'lon': float, 'name': str}
            or None if not found.
        """
        try:
            url = "https://geocoding-api.open-meteo.com/v1/search"
            params: dict[str, str | int] = {
                "name": query,
                "count": 1,
                "language": "fr",
                "format": "json",
            }
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=5.0)
                response.raise_for_status()
                data = response.json()

                if not data.get("results"):
                    return None

                result = data["results"][0]
                return {
                    "lat": result["latitude"],
                    "lon": result["longitude"],
                    "name": f"{result['name']}, {result.get('country', '')}",
                }
        except Exception:
            logger.exception(
                "Geocoding error in geocode_location",
            )
            return None

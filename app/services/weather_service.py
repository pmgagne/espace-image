import httpx
from typing import Dict


class WeatherService:
    # WMO Weather interpretation codes (WW)
    # https://open-meteo.com/en/docs
    WMO_CODES = {
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
    async def get_current_weather(lat: float, lon: float) -> Dict:
        """
        Fetches current weather from Open-Meteo.
        """
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5.0)
                response.raise_for_status()
                data = response.json()

                current = data.get("current_weather", {})
                temp = current.get("temperature")
                code = current.get("weathercode")

                condition = WeatherService.WMO_CODES.get(code, "Inconnu")

                return {
                    "temp": round(temp),
                    "condition": condition,
                    "location": f"{lat:.2f}, {lon:.2f}",  # Placeholder until reverse geocoding
                }
        except Exception as e:
            print(f"Weather API Error: {e}")
            return {
                "temp": "--",
                "condition": "Erreur",
                "location": "Service indisponible",
            }

    @staticmethod
    async def geocode_location(query: str) -> Dict | None:
        """
        Searches for a location name using Open-Meteo Geocoding API.
        Returns: {'lat': float, 'lon': float, 'name': str} or None
        """
        try:
            url = "https://geocoding-api.open-meteo.com/v1/search"
            params = {"name": query, "count": 1, "language": "fr", "format": "json"}
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
        except Exception as e:
            print(f"Geocoding Error: {e}")
            return None

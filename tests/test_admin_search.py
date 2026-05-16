from app.main import app as fastapi_app
from app.modules.settings.api.contracts import AppSettingsDTO, SettingsFormDTO
from app.modules.settings.api.interfaces import get_settings_service
from app.modules.weather.api.interfaces import (
    WeatherLocationResult,
    get_weather_service,
)


def test_admin_settings_search(client, session):
    class FakeWeatherService:
        async def geocode_location(self, query: str) -> WeatherLocationResult | None:
            assert query == "Paris"
            return WeatherLocationResult(lat=48.8566, lon=2.3522, name="Paris, France")

        async def geocode_for_settings(self, query: str) -> tuple[float | None, float | None, str]:
            result = await self.geocode_location(query)
            if result is None:
                return None, None, "Location not found"
            return result.lat, result.lon, result.name

    fastapi_app.dependency_overrides[get_weather_service] = lambda: FakeWeatherService()
    try:
        response = client.post("/admin/settings/search", data={"location_query": "Paris"})
    finally:
        fastapi_app.dependency_overrides.pop(get_weather_service, None)

    assert response.status_code == 200
    # Check that inputs are pre-filled with new values
    assert 'value="48.8566"' in response.text
    assert 'value="2.3522"' in response.text
    # Check that the detected name is displayed (based on the template logic)
    assert "Paris, France" in response.text


def test_admin_settings_partial_uses_weather_service(client):
    class FakeSettingsService:
        def get_settings(self):
            return AppSettingsDTO(
                active_preset_id=None,
                weather_latitude=48.8566,
                weather_longitude=2.3522,
                slideshow_duration=30,
            )

        def get_settings_form(self):
            return SettingsFormDTO(
                active_preset_id=None,
                weather_latitude=48.8566,
                weather_longitude=2.3522,
                slideshow_duration=30,
            )

        def list_presets(self):
            return []

        def get_settings_html(
            self,
            location_name: str | None,
            backend_timezone: str,
            form: SettingsFormDTO | None = None,
        ) -> str:
            _ = backend_timezone
            rendered_location = location_name or ""
            return f"<div>{rendered_location}</div>"

    class FakeWeatherService:
        async def geocode_location(self, query: str) -> WeatherLocationResult | None:
            return None

        async def reverse_geocode(self, lat: float, lon: float) -> str | None:
            assert lat == 48.8566
            assert lon == 2.3522
            return "Paris, Ile-de-France"

        async def get_location_name(self, lat: float | None, lon: float | None) -> str:
            if lat is None or lon is None:
                return ""
            return await self.reverse_geocode(lat, lon) or ""

    fastapi_app.dependency_overrides[get_settings_service] = lambda: FakeSettingsService()
    fastapi_app.dependency_overrides[get_weather_service] = lambda: FakeWeatherService()
    try:
        response = client.get("/admin/partials/settings")
    finally:
        fastapi_app.dependency_overrides.pop(get_settings_service, None)
        fastapi_app.dependency_overrides.pop(get_weather_service, None)

    assert response.status_code == 200
    assert "Paris, Ile-de-France" in response.text

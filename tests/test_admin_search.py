from app.db.models import AppSettings
from app.main import app as fastapi_app
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
        def get_settings(self, session):
            return AppSettings(weather_latitude=48.8566, weather_longitude=2.3522)

        def list_presets(self, session):
            return []

    class FakeWeatherService:
        async def geocode_location(self, query: str) -> WeatherLocationResult | None:
            return None

        async def reverse_geocode(self, lat: float, lon: float) -> str | None:
            assert lat == 48.8566
            assert lon == 2.3522
            return "Paris, Ile-de-France"

    fastapi_app.dependency_overrides[get_settings_service] = lambda: FakeSettingsService()
    fastapi_app.dependency_overrides[get_weather_service] = lambda: FakeWeatherService()
    try:
        response = client.get("/admin/partials/settings")
    finally:
        fastapi_app.dependency_overrides.pop(get_settings_service, None)
        fastapi_app.dependency_overrides.pop(get_weather_service, None)

    assert response.status_code == 200
    assert "Paris, Ile-de-France" in response.text

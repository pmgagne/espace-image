from app.main import app as fastapi_app
from app.modules.weather.api.interfaces import WeatherLocationResult, get_weather_service


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

from unittest.mock import patch


def test_admin_settings_search(client, session):
    # Mock the geocode service
    with patch("app.services.weather_service.WeatherService.geocode_location") as mock_geo:
        mock_geo.return_value = {"lat": 48.8566, "lon": 2.3522, "name": "Paris, France"}

        response = client.post("/admin/settings/search", data={"location_query": "Paris"})

        assert response.status_code == 200
        # Check that inputs are pre-filled with new values
        assert 'value="48.8566"' in response.text
        assert 'value="2.3522"' in response.text
        # Check that the detected name is displayed (based on the template logic)
        assert "Paris, France" in response.text

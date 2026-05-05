from sqlmodel import select

from app.db.models import AppSettings, Preset


def test_update_settings_invalid_latitude(client):
    response = client.put(
        "/api/v1/settings/weather-location",
        json={"latitude": 999, "longitude": None},
    )
    assert response.status_code == 422
    assert response.json().get("detail") == "Invalid latitude value"


def test_update_settings_invalid_longitude(client):
    response = client.put(
        "/api/v1/settings/weather-location",
        json={"latitude": None, "longitude": 999},
    )
    assert response.status_code == 422
    assert response.json().get("detail") == "Invalid longitude value"


def test_update_settings_invalid_duration(client):
    response = client.put(
        "/api/v1/settings/slideshow-duration",
        json={"slideshow_duration": 0},
    )
    assert response.status_code == 422
    assert response.json().get("detail") == "Duration must be a positive integer"


def test_update_settings_invalid_active_preset(client):
    # Use a preset id that doesn't exist
    response = client.put(
        "/api/v1/settings/active-preset",
        json={"active_preset_id": 999},
    )
    assert response.status_code == 422
    assert response.json().get("detail") == "Active preset not found"


def test_update_settings_valid_boundary_values(client, session):
    # Create a preset to reference
    preset = Preset(name="TestPreset")
    session.add(preset)
    session.commit()
    session.refresh(preset)

    response_location = client.put(
        "/api/v1/settings/weather-location",
        json={"latitude": 90, "longitude": 180},
    )
    assert response_location.status_code == 200

    response_preset = client.put(
        "/api/v1/settings/active-preset",
        json={"active_preset_id": preset.id},
    )
    assert response_preset.status_code == 200

    response_duration = client.put(
        "/api/v1/settings/slideshow-duration",
        json={"slideshow_duration": 45},
    )
    assert response_duration.status_code == 200

    settings = session.exec(select(AppSettings)).first()
    assert settings is not None
    assert settings.active_preset_id == preset.id
    assert settings.weather_latitude == 90.0
    assert settings.weather_longitude == 180.0
    assert settings.slideshow_duration == 45

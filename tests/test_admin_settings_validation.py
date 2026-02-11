from sqlmodel import select

from app.db.models import AppSettings, Preset


def test_update_settings_invalid_latitude(client):
    response = client.post("/admin/settings", data={"latitude": "999"})
    assert response.status_code == 422
    assert response.json().get("detail") == "Latitude must be between -90 and 90"


def test_update_settings_invalid_longitude(client):
    response = client.post("/admin/settings", data={"longitude": "999"})
    assert response.status_code == 422
    assert response.json().get("detail") == "Longitude must be between -180 and 180"


def test_update_settings_invalid_duration(client):
    response = client.post("/admin/settings", data={"duration": "0"})
    assert response.status_code == 422
    assert response.json().get("detail") == "Duration must be a positive integer"


def test_update_settings_invalid_active_preset(client):
    # Use a preset id that doesn't exist
    response = client.post("/admin/settings", data={"active_preset_id": "999"})
    assert response.status_code == 422
    assert response.json().get("detail") == "Active preset not found"


def test_update_settings_valid_boundary_values(client, session):
    # Create a preset to reference
    preset = Preset(name="TestPreset")
    session.add(preset)
    session.commit()
    session.refresh(preset)

    response = client.post(
        "/admin/settings",
        data={
            "active_preset_id": str(preset.id),
            "latitude": "90",
            "longitude": "180",
            "duration": "45",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == "/"

    settings = session.exec(select(AppSettings)).first()
    assert settings is not None
    assert settings.active_preset_id == preset.id
    assert settings.weather_latitude == 90.0
    assert settings.weather_longitude == 180.0
    assert settings.slideshow_duration == 45

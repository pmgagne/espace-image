from io import BytesIO

from PIL import Image
from sqlmodel import select

from app.db.models import AppSettings, Photo, Preset


def _make_jpeg_bytes() -> bytes:
    """Create a small in-memory JPEG payload for upload tests."""
    image = Image.new("RGB", (16, 16), color="green")
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_api_create_preset_returns_json_and_persists(client, session):
    """Create-preset API should return JSON and persist the preset row."""
    response = client.post("/api/v1/presets", json={"name": "API Preset"})

    assert response.status_code == 201
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["name"] == "API Preset"

    presets = session.exec(select(Preset).where(Preset.name == "API Preset")).all()
    assert len(presets) == 1


def test_api_upload_and_delete_image_round_trip(client, session):
    """Media API should upload an image and then delete it through JSON endpoints."""
    preset = Preset(name="Upload Target")
    session.add(preset)
    session.commit()
    session.refresh(preset)

    response = client.post(
        f"/api/v1/presets/{preset.id}/images",
        files={"files": ("test.jpg", _make_jpeg_bytes(), "image/jpeg")},
    )

    assert response.status_code == 201
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert len(payload) == 1
    image_id = payload[0]["id"]

    photo = session.get(Photo, image_id)
    assert photo is not None

    metadata_response = client.get(f"/api/v1/images/{image_id}/metadata")
    assert metadata_response.status_code == 200
    assert metadata_response.json()["preset_id"] == preset.id

    delete_response = client.delete(f"/api/v1/images/{image_id}")
    assert delete_response.status_code == 204

    session.expire_all()
    assert session.get(Photo, image_id) is None


def test_api_get_settings_returns_json(client):
    """Settings API should return JSON null when no settings row exists yet."""
    response = client.get("/api/v1/settings")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() is None


def test_api_set_active_preset_updates_settings(client, session):
    """Active preset API should persist only the requested settings mutation."""
    preset = Preset(name="Active Preset")
    session.add(preset)
    session.commit()
    session.refresh(preset)

    response = client.put(
        "/api/v1/settings/active-preset",
        json={"active_preset_id": preset.id},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["active_preset_id"] == preset.id
    assert response.json()["slideshow_duration"] == 30

    settings = session.exec(select(AppSettings)).first()
    assert settings is not None
    assert settings.active_preset_id == preset.id


def test_api_set_slideshow_duration_reuses_existing_validation(client):
    """Duration API should preserve the existing validation error semantics."""
    response = client.put(
        "/api/v1/settings/slideshow-duration",
        json={"slideshow_duration": 0},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Duration must be a positive integer"


def test_api_v1_routes_return_json_not_html(client):
    """API v1 routes should return JSON payloads for non-empty responses."""
    settings_response = client.get("/api/v1/settings")
    assert settings_response.status_code == 200
    assert settings_response.headers["content-type"].startswith("application/json")

    presets_response = client.get("/api/v1/settings/presets")
    assert presets_response.status_code == 200
    assert presets_response.headers["content-type"].startswith("application/json")

    create_response = client.post("/api/v1/presets", json={"name": "JSON Contract Preset"})
    assert create_response.status_code == 201
    assert create_response.headers["content-type"].startswith("application/json")


def test_api_create_and_delete_preset_removes_photos(client, session):
    """Creating a preset via API then deleting it should remove the preset and its photos."""
    # Create preset through API
    response = client.post("/api/v1/presets", json={"name": "ToDeletePreset"})
    assert response.status_code == 201
    payload = response.json()
    preset_id = payload["id"]

    # Add a photo row referencing the preset (simulates uploaded photo)
    photo = Photo(filename="orphan.jpg", preset_id=preset_id)
    session.add(photo)
    session.commit()
    session.refresh(photo)
    photo_id = photo.id

    # Ensure DB rows exist
    assert session.get(Photo, photo_id) is not None
    assert session.get(Preset, preset_id) is not None

    # Delete the preset via API
    delete_resp = client.delete(f"/api/v1/presets/{preset_id}")
    assert delete_resp.status_code == 204

    # Verify preset and photo rows are removed from the DB
    session.expire_all()
    assert session.get(Preset, preset_id) is None
    assert session.get(Photo, photo_id) is None

from io import BytesIO
from pathlib import Path

from PIL import Image


def _make_jpeg_bytes() -> bytes:
    image = Image.new("RGB", (16, 16), color="blue")
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_integration_upload_then_delete_removes_file(client, session):
    """End-to-end: upload file, assert it's on disk, delete preset, assert file removed."""
    # Create preset via API
    create = client.post("/api/v1/presets", json={"name": "IntegrationPreset"})
    assert create.status_code == 201
    preset = create.json()
    preset_id = preset["id"]
    preset_name = preset["name"]

    # Upload one image to the preset
    resp = client.post(
        f"/api/v1/presets/{preset_id}/images",
        files={"files": ("upload.jpg", _make_jpeg_bytes(), "image/jpeg")},
    )
    assert resp.status_code == 201
    payload = resp.json()
    assert len(payload) == 1
    filename = payload[0]["filename"]
    photo_id = payload[0]["id"]

    # Ensure file exists on disk under data/uploads/<preset_name>/<filename>
    upload_path = Path("data") / "uploads" / preset_name / filename
    assert upload_path.exists(), f"Expected uploaded file at {upload_path}"

    # Delete the preset via API
    del_resp = client.delete(f"/api/v1/presets/{preset_id}")
    assert del_resp.status_code == 204

    # File should be removed from disk
    assert not upload_path.exists(), "Uploaded file should be deleted after preset removal"

    # DB rows removed
    session.expire_all()
    from app.db.models import Photo, Preset

    assert session.get(Preset, preset_id) is None
    assert session.get(Photo, photo_id) is None


def test_api_delete_non_existent_preset_returns_404(client):
    resp = client.delete("/api/v1/presets/99999")
    assert resp.status_code == 404

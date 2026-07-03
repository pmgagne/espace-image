"""Tests for the GET /images/{photo_id} serving route, in particular the
legacy (iPad 2) downscaling behavior."""

from io import BytesIO

from PIL import Image

from app.db.models import Preset


def _make_large_jpeg_bytes(width: int = 2000, height: int = 1500) -> bytes:
    """Create an in-memory JPEG larger than the legacy max dimension."""
    image = Image.new("RGB", (width, height), color="red")
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def test_legacy_mode_downscales_image(client, session, monkeypatch):
    """`mode=legacy` must return an image capped at the configured max dimension,
    while the default (modern) mode preserves the original resolution."""
    monkeypatch.setenv("IMAGE_LEGACY_MAX_DIMENSION", "1024")

    preset = Preset(name="Legacy Dimension Test")
    session.add(preset)
    session.commit()
    session.refresh(preset)

    upload_response = client.post(
        f"/api/v1/presets/{preset.id}/images",
        files={"files": ("big.jpg", _make_large_jpeg_bytes(2000, 1500), "image/jpeg")},
    )
    assert upload_response.status_code == 201
    image_id = upload_response.json()[0]["id"]

    try:
        modern_response = client.get(f"/images/{image_id}")
        assert modern_response.status_code == 200
        with Image.open(BytesIO(modern_response.content)) as img:
            assert img.size == (2000, 1500)

        legacy_response = client.get(f"/images/{image_id}?mode=legacy")
        assert legacy_response.status_code == 200
        with Image.open(BytesIO(legacy_response.content)) as img:
            width, height = img.size
            assert max(width, height) == 1024
            # Aspect ratio preserved (2000x1500 -> 4:3)
            assert round(width / height, 2) == round(2000 / 1500, 2)
    finally:
        client.delete(f"/api/v1/images/{image_id}")

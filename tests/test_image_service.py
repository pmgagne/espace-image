from io import BytesIO

import pytest
from PIL import Image

from app.modules.media.internal.infrastructure.image_ops import (
    GalleryManager,
    ImageOptimizer,
)


@pytest.fixture
def jpeg_bytes():
    """Creates an in-memory JPEG for testing."""
    img = Image.new("RGB", (640, 480), color="red")
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()


@pytest.fixture
def png_bytes():
    """Creates an in-memory PNG for testing."""
    img = Image.new("RGB", (320, 240), color="blue")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def test_optimize_bytes_preserves_dimensions(monkeypatch, jpeg_bytes):
    """Test that optimization preserves pixel dimensions."""
    monkeypatch.setenv("IMAGE_OPTIMIZE_MIN_BYTES", "1")
    monkeypatch.setenv("IMAGE_JPEG_QUALITY", "82")

    optimized = ImageOptimizer.optimize_bytes(jpeg_bytes)

    with Image.open(BytesIO(optimized)) as img:
        width, height = img.size
        assert (width, height) == (640, 480)


def test_optimize_bytes_downscales_when_max_dimension_set(monkeypatch):
    """Test that a max_dimension cap downscales oversized images (aspect preserved)."""
    monkeypatch.setenv("IMAGE_OPTIMIZE_MIN_BYTES", "10000000")

    img = Image.new("RGB", (2000, 1500), color="green")
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=90)
    large_bytes = buffer.getvalue()

    optimized = ImageOptimizer.optimize_bytes(large_bytes, max_dimension=1024)

    with Image.open(BytesIO(optimized)) as result_img:
        width, height = result_img.size
        assert max(width, height) == 1024
        assert round(width / height, 2) == round(2000 / 1500, 2)


def test_optimize_bytes_preserves_dimensions_when_under_max_dimension(monkeypatch, jpeg_bytes):
    """Test that a max_dimension cap is a no-op when the image is already smaller."""
    monkeypatch.setenv("IMAGE_OPTIMIZE_MIN_BYTES", "10000000")

    optimized = ImageOptimizer.optimize_bytes(jpeg_bytes, max_dimension=1024)

    with Image.open(BytesIO(optimized)) as img:
        assert img.size == (640, 480)


def test_optimize_bytes_noop_under_threshold(monkeypatch, jpeg_bytes):
    """Test that images under the threshold are not re-encoded."""
    monkeypatch.setenv("IMAGE_OPTIMIZE_MIN_BYTES", "10000000")
    optimized = ImageOptimizer.optimize_bytes(jpeg_bytes)
    assert optimized == jpeg_bytes


def test_optimize_bytes_reencodes_over_threshold(monkeypatch, jpeg_bytes):
    """Test that JPEGs over the threshold are re-encoded."""
    monkeypatch.setenv("IMAGE_OPTIMIZE_MIN_BYTES", "1")
    monkeypatch.setenv("IMAGE_JPEG_QUALITY", "82")

    optimized = ImageOptimizer.optimize_bytes(jpeg_bytes)

    assert optimized != jpeg_bytes
    with Image.open(BytesIO(optimized)) as img:
        assert img.format == "JPEG"


def test_gallery_manager_save(tmp_path, monkeypatch, jpeg_bytes):
    """Test saving an upload."""
    # Use a temp dir for uploads
    upload_dir = tmp_path / "uploads"
    manager = GalleryManager(upload_dir=str(upload_dir))
    filename = "test.jpg"

    monkeypatch.setenv("IMAGE_OPTIMIZE_MIN_BYTES", "10000000")
    saved_path, stored_filename = manager.save_upload(jpeg_bytes, filename)

    assert saved_path.exists()
    assert saved_path.read_bytes() == jpeg_bytes
    assert saved_path.parent.name == "Default"
    assert stored_filename == filename


def test_gallery_manager_reencodes_non_jpeg(tmp_path, monkeypatch, png_bytes):
    """Test that non-JPEG uploads are re-encoded and renamed."""
    upload_dir = tmp_path / "uploads"
    manager = GalleryManager(upload_dir=str(upload_dir))
    filename = "test.png"

    monkeypatch.setenv("IMAGE_OPTIMIZE_MIN_BYTES", "10000000")
    saved_path, stored_filename = manager.save_upload(png_bytes, filename)

    assert saved_path.exists()
    assert stored_filename.endswith(".jpg")
    with Image.open(saved_path) as img:
        assert img.format == "JPEG"


def test_gallery_manager_delete(tmp_path, monkeypatch, jpeg_bytes):
    """Test deleting a photo from disk."""
    upload_dir = tmp_path / "uploads"
    manager = GalleryManager(upload_dir=str(upload_dir))
    filename = "test.jpg"
    preset_name = "TestPreset"

    monkeypatch.setenv("IMAGE_OPTIMIZE_MIN_BYTES", "10000000")
    saved_path, _ = manager.save_upload(jpeg_bytes, filename, preset_name)

    assert saved_path.exists()

    # Delete the photo
    result = manager.delete_photo(filename, preset_name)
    assert result is True
    assert not saved_path.exists()

    # Try deleting again (should return False)
    result = manager.delete_photo(filename, preset_name)
    assert result is False


def test_gallery_manager_rejects_invalid_extension(tmp_path, monkeypatch, jpeg_bytes):
    """Test that uploads with unsupported extensions are rejected early."""
    upload_dir = tmp_path / "uploads"
    manager = GalleryManager(upload_dir=str(upload_dir))
    filename = "malicious.pdf"

    monkeypatch.setenv("IMAGE_OPTIMIZE_MIN_BYTES", "10000000")
    with pytest.raises(ValueError) as exc:
        manager.save_upload(jpeg_bytes, filename)

    assert "not allowed" in str(exc.value)


def test_gallery_manager_accepts_uppercase_extension(tmp_path, monkeypatch, jpeg_bytes):
    """Test that extension check is case-insensitive."""
    upload_dir = tmp_path / "uploads"
    manager = GalleryManager(upload_dir=str(upload_dir))
    filename = "test.JPG"

    monkeypatch.setenv("IMAGE_OPTIMIZE_MIN_BYTES", "10000000")
    saved_path, stored_filename = manager.save_upload(jpeg_bytes, filename)

    assert saved_path.exists()
    assert stored_filename.lower().endswith(".jpg")

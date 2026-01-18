import os
import pytest
from PIL import Image
from pathlib import Path
from app.services.image_service import ImageOptimizer, GalleryManager

@pytest.fixture
def sample_image(tmp_path):
    """Creates a large sample image for testing."""
    img_path = tmp_path / "test_large.jpg"
    # Create a 2000x2000 red image
    img = Image.new("RGB", (2000, 2000), color="red")
    img.save(img_path)
    return img_path

def test_resize_for_legacy(sample_image):
    """Test that images are resized to fit 1024x768."""
    resized_io = ImageOptimizer.resize_for_legacy(sample_image)
    
    with Image.open(resized_io) as img:
        width, height = img.size
        assert width <= 1024
        assert height <= 768
        # Since original was square 2000x2000, resized should be 768x768 (limited by height)
        assert height == 768
        assert width == 768

def test_gallery_manager_save(tmp_path):
    """Test saving an upload."""
    # Use a temp dir for uploads
    upload_dir = tmp_path / "uploads"
    manager = GalleryManager(upload_dir=str(upload_dir))
    
    content = b"fake image content"
    filename = "test.jpg"
    
    saved_path = manager.save_upload(content, filename)
    
    assert saved_path.exists()
    assert saved_path.read_bytes() == content
    assert saved_path.parent.name == "Default"

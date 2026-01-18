import os
from PIL import Image
from io import BytesIO
from pathlib import Path

LEGACY_MAX_WIDTH = 1024
LEGACY_MAX_HEIGHT = 768

class ImageOptimizer:
    @staticmethod
    def resize_for_legacy(image_path: str | Path) -> BytesIO:
        """
        Resizes an image to fit within 1024x768 while preserving aspect ratio.
        Returns the image data as a BytesIO object (JPEG).
        """
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary (e.g. for PNGs with transparency)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                img.thumbnail((LEGACY_MAX_WIDTH, LEGACY_MAX_HEIGHT), Image.Resampling.LANCZOS)
                
                output = BytesIO()
                # Optimize and save as JPEG
                img.save(output, format="JPEG", quality=85, optimize=True)
                output.seek(0)
                return output
        except Exception as e:
            # In a real app, log this error
            print(f"Error resizing image {image_path}: {e}")
            raise e

class GalleryManager:
    def __init__(self, upload_dir: str = "data/uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def save_upload(self, file_content: bytes, filename: str, preset_name: str = "Default") -> Path:
        """
        Saves an uploaded file to the specific preset folder.
        """
        preset_dir = self.upload_dir / preset_name
        preset_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = preset_dir / filename
        with open(file_path, "wb") as f:
            f.write(file_content)
            
        return file_path

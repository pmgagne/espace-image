import os
from io import BytesIO
from pathlib import Path

import pillow_heif
from PIL import Image

# Register HEIF opener to support .heic files
pillow_heif.register_heif_opener()

DEFAULT_OPTIMIZE_MIN_BYTES = 800 * 1024
DEFAULT_JPEG_QUALITY = 82
DEFAULT_JPEG_MIN_QUALITY = 60


def _get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


class ImageOptimizer:
    @staticmethod
    def optimize_bytes(file_content: bytes) -> bytes:
        """
        Re-encode to JPEG if the content exceeds the configured size threshold.
        Pixel dimensions are preserved.
        """
        optimize_min_bytes = _get_env_int("IMAGE_OPTIMIZE_MIN_BYTES", DEFAULT_OPTIMIZE_MIN_BYTES)
        jpeg_quality = _get_env_int("IMAGE_JPEG_QUALITY", DEFAULT_JPEG_QUALITY)
        jpeg_min_quality = _get_env_int("IMAGE_JPEG_MIN_QUALITY", DEFAULT_JPEG_MIN_QUALITY)

        try:
            with Image.open(BytesIO(file_content)) as img:
                format_name = (img.format or "").upper()
                is_jpeg = format_name == "JPEG"
                should_reencode = (not is_jpeg) or (len(file_content) > optimize_min_bytes)

                if not should_reencode:
                    return file_content

                image = img.convert("RGB") if img.mode != "RGB" else img

                min_quality = min(jpeg_quality, jpeg_min_quality)
                quality = jpeg_quality
                output = BytesIO()
                image.save(output, format="JPEG", quality=quality, optimize=True)
                optimized = output.getvalue()

                if len(optimized) <= optimize_min_bytes:
                    return optimized

                target_quality = quality
                while len(optimized) > optimize_min_bytes and target_quality > min_quality:
                    target_quality = max(min_quality, target_quality - 5)
                    output = BytesIO()
                    image.save(output, format="JPEG", quality=target_quality, optimize=True)
                    optimized = output.getvalue()

                return optimized
        except Exception as e:
            print(f"Error optimizing image bytes: {e}")
            raise e

    @staticmethod
    def optimize_upload(file_content: bytes, filename: str) -> tuple[bytes, str]:
        optimized_content = ImageOptimizer.optimize_bytes(file_content)

        if optimized_content is file_content:
            return optimized_content, filename

        if filename.lower().endswith((".jpg", ".jpeg")):
            return optimized_content, filename

        new_filename = f"{Path(filename).stem}.jpg"
        return optimized_content, new_filename

    @staticmethod
    def optimize_path(image_path: str | Path) -> bytes:
        return ImageOptimizer.optimize_bytes(Path(image_path).read_bytes())


class GalleryManager:
    def __init__(self, upload_dir: str = "data/uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save_upload(
        self, file_content: bytes, filename: str, preset_name: str = "Default"
    ) -> tuple[Path, str]:
        """
        Saves an uploaded file to the specific preset folder.
        """
        preset_dir = self.upload_dir / preset_name
        preset_dir.mkdir(parents=True, exist_ok=True)

        optimized_content, stored_filename = ImageOptimizer.optimize_upload(file_content, filename)
        file_path = preset_dir / stored_filename
        with open(file_path, "wb") as f:
            f.write(optimized_content)

        return file_path, stored_filename

import logging
import os
from io import BytesIO
from pathlib import Path

try:
    import pillow_heif  # type: ignore
except Exception:
    pillow_heif = None  # type: ignore[assignment]

from PIL import Image

# Register HEIF opener to support .heic files when available.
if pillow_heif is not None:
    try:
        from typing import Any, cast

        cast(Any, pillow_heif).register_heif_opener()
    except Exception:
        logging.getLogger(__name__).debug(
            "Failed to register HEIF opener",
            exc_info=True,
        )

DEFAULT_OPTIMIZE_MIN_BYTES = 800 * 1024
DEFAULT_JPEG_QUALITY = 82
DEFAULT_JPEG_MIN_QUALITY = 60


# Allowed upload file extensions (lowercase, include leading dot)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif"}


def _get_env_int(name: str, default: int) -> int:
    """
    Get an integer value from the environment, or return a default
    if unset or invalid.

    Args:
        name (str): Environment variable name.
        default (int): Default value if not set or invalid.

    Returns:
        int: The integer value from the environment or the default.
    """
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


logger = logging.getLogger(__name__)


class ImageOptimizer:
    """
    Static utility class for optimizing image bytes and uploads for
    storage and display.
    """

    @staticmethod
    def optimize_bytes(file_content: bytes) -> bytes:
        """
        Re-encode to JPEG if the content exceeds the configured size threshold.
        Pixel dimensions are preserved.

        Args:
            file_content (bytes): The image file content.

        Returns:
            bytes: Optimized image bytes (possibly re-encoded as JPEG).
        """
        optimize_min_bytes = _get_env_int(
            "IMAGE_OPTIMIZE_MIN_BYTES",
            DEFAULT_OPTIMIZE_MIN_BYTES,
        )
        jpeg_quality = _get_env_int(
            "IMAGE_JPEG_QUALITY",
            DEFAULT_JPEG_QUALITY,
        )
        jpeg_min_quality = _get_env_int(
            "IMAGE_JPEG_MIN_QUALITY",
            DEFAULT_JPEG_MIN_QUALITY,
        )

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
                image.save(
                    output,
                    format="JPEG",
                    quality=quality,
                    optimize=True,
                )
                optimized = output.getvalue()

                if len(optimized) <= optimize_min_bytes:
                    return optimized

                target_quality = quality
                while len(optimized) > optimize_min_bytes and target_quality > min_quality:
                    target_quality = max(min_quality, target_quality - 5)
                    output = BytesIO()
                    image.save(
                        output,
                        format="JPEG",
                        quality=target_quality,
                        optimize=True,
                    )
                    optimized = output.getvalue()

                return optimized
        except Exception:
            logger.exception("Error optimizing image bytes")
            raise

    @staticmethod
    def optimize_upload(
        file_content: bytes,
        filename: str,
    ) -> tuple[bytes, str]:
        """
        Optimize an uploaded image and return the new content and filename.

        Args:
            file_content (bytes): The image file content.
            filename (str): The original filename.

        Returns:
            tuple[bytes, str]: (optimized content, possibly new filename)
        """
        optimized_content = ImageOptimizer.optimize_bytes(file_content)

        if optimized_content is file_content:
            return optimized_content, filename

        if filename.lower().endswith((".jpg", ".jpeg")):
            return optimized_content, filename

        new_filename = f"{Path(filename).stem}.jpg"
        return optimized_content, new_filename

    @staticmethod
    def optimize_path(image_path: str | Path) -> bytes:
        """
        Optimize an image file at the given path and return the
        optimized bytes.

        Args:
            image_path (str | Path): Path to the image file.

        Returns:
            bytes: Optimized image bytes.
        """
        return ImageOptimizer.optimize_bytes(Path(image_path).read_bytes())


class GalleryManager:
    """
    Manages gallery uploads and deletions, storing files in
    preset-specific folders.
    """

    def __init__(self, upload_dir: str = "data/uploads"):
        """
        Initialize the GalleryManager.

        Args:
            upload_dir (str): Directory to store uploads.
        """
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save_upload(
        self, file_content: bytes, filename: str, preset_name: str = "Default"
    ) -> tuple[Path, str]:
        """
        Save an uploaded file to the specific preset folder.

        Args:
            file_content (bytes): The image file content.
            filename (str): The original filename.
            preset_name (str): The preset folder name.

        Returns:
            tuple[Path, str]: (file path, stored filename)
        """
        preset_dir = self.upload_dir / preset_name
        preset_dir.mkdir(parents=True, exist_ok=True)

        # Validate file extension before any processing
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
            raise ValueError(
                f"File type {ext or '(no extension)'} not allowed. Supported: {allowed}"
            )

        # Security: Validate file content is actually an image (magic byte validation)
        # PIL will raise an exception if the file is not a valid image format
        try:
            with Image.open(BytesIO(file_content)) as img:
                img.verify()  # Verify image integrity
                # Check that detected format matches allowed types
                detected_format = (img.format or "").upper()
                allowed_formats = {"JPEG", "PNG", "HEIC", "HEIF"}
                if detected_format not in allowed_formats:
                    raise ValueError(
                        f"Invalid image format detected: {detected_format}. "
                        f"Expected one of: {', '.join(allowed_formats)}"
                    )
        except ValueError:
            raise
        except Exception as e:
            logger.warning("Image validation failed for %s: %s", filename, e)
            raise ValueError("File validation failed: not a valid image file") from e

        optimized_content, stored_filename = ImageOptimizer.optimize_upload(
            file_content,
            filename,
        )
        file_path = preset_dir / stored_filename
        with open(file_path, "wb") as f:
            f.write(optimized_content)

        return file_path, stored_filename

    def delete_photo(
        self,
        filename: str,
        preset_name: str = "Default",
    ) -> bool:
        """
        Delete a photo file from the specific preset folder.

        Args:
            filename (str): The filename to delete.
            preset_name (str): The preset folder name.

        Returns:
            bool: True if the file was deleted, False if it didn't exist.
        """
        preset_dir = self.upload_dir / preset_name
        file_path = preset_dir / filename

        if file_path.exists():
            file_path.unlink()
            return True
        return False

"""Media module service implementation."""

from pathlib import Path

from app.modules.media.api.interfaces import IMediaService
from app.modules.media.internal.infrastructure.image_ops import GalleryManager, ImageOptimizer


class MediaModuleService(IMediaService):
    """Adapter service for media file operations during migration."""

    def __init__(self) -> None:
        """Initialize media adapters with current upload storage settings."""
        self._gallery_manager = GalleryManager()

    def optimize_path(self, image_path: str | Path) -> bytes:
        """Return optimized image bytes for a given image path."""
        return ImageOptimizer.optimize_path(image_path)

    def save_upload(
        self,
        file_content: bytes,
        filename: str,
        preset_name: str = "Default",
    ) -> tuple[Path, str]:
        """Save upload and return stored path and filename."""
        return self._gallery_manager.save_upload(file_content, filename, preset_name)

    def delete_photo(self, filename: str, preset_name: str = "Default") -> bool:
        """Delete file from storage and return deletion status."""
        return self._gallery_manager.delete_photo(filename, preset_name)


def create_media_service() -> IMediaService:
    """Factory that returns the media service implementation."""
    return MediaModuleService()

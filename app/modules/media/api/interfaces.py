"""Public interfaces for the media module."""

from pathlib import Path
from typing import Protocol


class IMediaService(Protocol):
    """Public interface for media processing and file operations."""

    def optimize_path(self, image_path: str | Path) -> bytes:
        """Return optimized image bytes for a given image path."""

    def save_upload(
        self,
        file_content: bytes,
        filename: str,
        preset_name: str = "Default",
    ) -> tuple[Path, str]:
        """Save an uploaded image and return path plus stored filename."""

    def delete_photo(self, filename: str, preset_name: str = "Default") -> bool:
        """Delete an image file from storage."""


def get_media_service() -> IMediaService:
    """Dependency injection token for media service."""
    raise NotImplementedError("Media service not initialized")

"""Public interfaces for the media module."""

from pathlib import Path
from typing import Any, Protocol

from fastapi import UploadFile

from app.modules.media.api.contracts import (
    PhotoDTO,
    PresetDTO,
)


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

    async def create_preset(self, name: str) -> PresetDTO:
        """
        Create a new preset.

        Args:
            name: Preset name.

        Returns:
            Created Preset.
        """
        ...

    async def upload_photos(self, preset_id: int, files: list[UploadFile]) -> list[PhotoDTO]:
        """
        Upload photos to a preset.

        Args:
            preset_id: Preset ID.
            files: List of uploaded files.

        Returns:
            List of created Photo records.

        Raises:
            ValueError: If preset not found or file validation fails.
        """
        ...

    async def delete_photo_from_db(self, photo_id: int) -> bool:
        """
        Delete a photo record from database.

        Args:
            photo_id: Photo ID.

        Returns:
            True if deleted, False if not found.
        """
        ...

    async def delete_preset(self, preset_id: int) -> bool:
        """
        Delete a preset and all its photos from storage and the database.

        Args:
            preset_id: Preset ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        ...

    async def get_gallery_for_ui(self, preset_id: int | None = None) -> dict[str, Any]:
        """
        Get presets and photos formatted for gallery UI rendering.

        Args:
            preset_id: Optional preset ID to select by default.

        Returns:
            Dictionary with 'presets', 'selected_preset', and 'photos' for template.
        """
        ...

    async def get_photo_for_download(self, photo_id: int) -> dict[str, Any]:
        """
        Get photo with eager-loaded preset relationship for download.

        Args:
            photo_id: Photo ID.

        Returns:
            Dictionary with 'photo', 'preset_name', and 'file_path'.
        """
        ...

    async def get_photo_by_id(self, photo_id: int) -> PhotoDTO | None:
        """
        Get a photo by ID without eager-loading (for validation).

        Args:
            photo_id: Photo ID.

        Returns:
            Photo record or None if not found.
        """
        ...

    async def get_image_payload(self, photo_id: int) -> dict[str, bytes]:
        """Return optimized image bytes for serving."""
        ...


def get_media_service() -> IMediaService:
    """Dependency injection token for media service."""
    raise NotImplementedError("Media service not initialized")

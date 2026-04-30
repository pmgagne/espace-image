"""Public interfaces for the media module."""

from pathlib import Path
from typing import Any, Protocol

from fastapi import UploadFile
from sqlmodel import Session

from app.db.models import Photo, Preset


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

    async def create_preset(self, session: Session, name: str) -> Preset:
        """
        Create a new preset.

        Args:
            session: Database session.
            name: Preset name.

        Returns:
            Created Preset.
        """
        ...

    async def upload_photos(
        self, session: Session, preset_id: int, files: list[UploadFile]
    ) -> list[Photo]:
        """
        Upload photos to a preset.

        Args:
            session: Database session.
            preset_id: Preset ID.
            files: List of uploaded files.

        Returns:
            List of created Photo records.

        Raises:
            ValueError: If preset not found or file validation fails.
        """
        ...

    async def delete_photo_from_db(self, session: Session, photo_id: int) -> bool:  # noqa: ARG002
        """
        Delete a photo record from database.

        Args:
            session: Database session.
            photo_id: Photo ID.

        Returns:
            True if deleted, False if not found.
        """
        ...

        async def get_gallery_for_ui(
            self, session: Session, preset_id: int | None = None
        ) -> dict[str, Any]:
            """
            Get presets and photos formatted for gallery UI rendering.

            Args:
                session: Database session.
                preset_id: Optional preset ID to select by default.

            Returns:
                Dictionary with 'presets', 'selected_preset', and 'photos' for template.
            """
            ...

        async def get_photo_for_download(self, session: Session, photo_id: int) -> dict[str, Any]:
            """
            Get photo with eager-loaded preset relationship for download.

            Args:
                session: Database session.
                photo_id: Photo ID.

            Returns:
                Dictionary with 'photo', 'preset_name', and 'file_path'.
            """
            ...

        async def get_photo_by_id(self, session: Session, photo_id: int) -> Photo | None:
            """
            Get a photo by ID without eager-loading (for validation).

            Args:
                session: Database session.
                photo_id: Photo ID.

            Returns:
                Photo record or None if not found.
            """
            ...


def get_media_service() -> IMediaService:
    """Dependency injection token for media service."""
    raise NotImplementedError("Media service not initialized")

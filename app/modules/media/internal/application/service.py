"""Media module service implementation."""

from pathlib import Path

from fastapi import UploadFile
from sqlmodel import Session

from app.db.models import Photo, Preset
from app.modules.media.api.interfaces import IMediaService
from app.modules.media.internal.infrastructure.image_ops import (
    GalleryManager,
    ImageOptimizer,
)


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

    async def create_preset(self, session: Session, name: str) -> Preset:
        """Create a new preset."""
        preset = Preset(name=name)
        session.add(preset)
        session.commit()
        session.refresh(preset)
        return preset

    async def upload_photos(
        self, session: Session, preset_id: int, files: list[UploadFile]
    ) -> list[Photo]:
        """Upload photos to a preset."""
        preset = session.get(Preset, preset_id)
        if not preset:
            msg = f"Preset {preset_id} not found"
            raise ValueError(msg)

        photos: list[Photo] = []
        for file in files:
            if not file.filename:
                continue
            content = await file.read()
            _path, stored_filename = self.save_upload(content, file.filename, preset.name)
            photo = Photo(filename=stored_filename, preset_id=preset_id)
            session.add(photo)
            photos.append(photo)

        session.commit()
        for photo in photos:
            session.refresh(photo)
        return photos

    async def delete_photo_from_db(self, session: Session, photo_id: int) -> bool:
        """Delete a photo record from database."""
        photo = session.get(Photo, photo_id)
        if not photo:
            return False

        # Delete from disk
        preset_name = photo.preset.name if photo.preset else "Default"
        self.delete_photo(photo.filename, preset_name)

        # Delete from DB
        session.delete(photo)
        session.commit()
        return True


def create_media_service() -> IMediaService:
    """Factory that returns the media service implementation."""
    return MediaModuleService()

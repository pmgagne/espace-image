"""Media module service implementation."""

from contextlib import contextmanager
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlmodel import Session

from app.db.models import Photo, Preset
from app.db.session_factory import SessionFactory
from app.modules.media.api.contracts import PhotoDTO, PresetDTO
from app.modules.media.api.interfaces import IMediaService
from app.modules.media.api.presenters import IMediaPresenter
from app.modules.media.api.repositories import IMediaRepository
from app.modules.media.api.storage import IMediaStorage
from app.modules.media.internal.infrastructure.image_ops import (
    ImageOptimizer,
)


class MediaModuleService(IMediaService):
    """Adapter service for media file operations during migration."""

    def __init__(
        self,
        session_factory: SessionFactory,
        repository: IMediaRepository,
        storage: IMediaStorage,
        presenter: IMediaPresenter,
    ) -> None:
        """Initialize media adapters with session factory and storage settings."""
        self._session_factory = session_factory
        self._repository = repository
        self._storage = storage
        self._presenter = presenter
        self._upload_dir = Path("data/uploads")

    @contextmanager
    def _session_scope(self, session: Session | None = None):
        """Yield provided session or create a local database session."""
        if session is not None:
            yield session
            return
        with self._session_factory.session_scope() as local_session:
            yield local_session

    @staticmethod
    def _preset_to_dto(preset: Preset) -> PresetDTO:
        """Convert Preset ORM to PresetDTO."""
        return PresetDTO(id=preset.id, name=preset.name)

    @staticmethod
    def _photo_to_dto(photo: Photo) -> PhotoDTO:
        """Convert Photo ORM to PhotoDTO."""
        return PhotoDTO(id=photo.id, preset_id=photo.preset_id, filename=photo.filename)

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
        return self._storage.save_upload(file_content, filename, preset_name)

    def delete_photo(self, filename: str, preset_name: str = "Default") -> bool:
        """Delete file from storage and return deletion status."""
        return self._storage.delete_photo(filename, preset_name)

    async def create_preset(self, name: str, session: Session | None = None) -> PresetDTO:
        """Create a new preset."""
        with self._session_scope(session) as active_session:
            preset = self._repository.create_preset(active_session, name)
            return self._preset_to_dto(preset)

    async def upload_photos(
        self,
        preset_id: int,
        files: list[UploadFile],
        session: Session | None = None,
    ) -> list[PhotoDTO]:
        """Upload photos to a preset."""
        with self._session_scope(session) as active_session:
            preset = self._repository.get_preset(active_session, preset_id)
            if not preset:
                msg = f"Preset {preset_id} not found"
                raise ValueError(msg)

            photos: list[Photo] = []
            for file in files:
                if not file.filename:
                    continue
                content = await file.read()
                _path, stored_filename = self.save_upload(content, file.filename, preset.name)
                photo = self._repository.add_photo(active_session, stored_filename, preset_id)
                photos.append(photo)

            self._repository.commit(active_session)
            for photo in photos:
                self._repository.refresh_photo(active_session, photo)
            return [self._photo_to_dto(p) for p in photos]

    async def delete_photo_from_db(self, photo_id: int, session: Session | None = None) -> bool:
        """Delete a photo record from database."""
        with self._session_scope(session) as active_session:
            photo = self._repository.get_photo(active_session, photo_id)
            if not photo:
                return False

            # Delete from disk
            preset_name = photo.preset.name if photo.preset else "Default"
            self.delete_photo(photo.filename, preset_name)

            # Delete from DB
            self._repository.delete_photo(active_session, photo)
            self._repository.commit(active_session)
            return True

    async def get_gallery_for_ui(
        self,
        preset_id: int | None = None,
        session: Session | None = None,
    ) -> dict[str, Any]:
        """Get presets and photos formatted for gallery UI rendering."""
        with self._session_scope(session) as active_session:
            presets = self._repository.list_presets(active_session)
            selected_preset = None
            photos: list[Photo] = []

            if preset_id:
                selected_preset = self._repository.get_preset(active_session, preset_id)
                if selected_preset:
                    photos = self._repository.list_photos_for_preset(
                        active_session,
                        selected_preset.id,
                    )
            elif presets:
                # Default to first preset if available
                selected_preset = presets[0]
                photos = self._repository.list_photos_for_preset(
                    active_session,
                    selected_preset.id,
                )

            return {
                "presets": [self._preset_to_dto(p) for p in presets],
                "selected_preset": self._preset_to_dto(selected_preset)
                if selected_preset
                else None,
                "photos": [self._photo_to_dto(p) for p in photos],
            }

    async def get_gallery_html(
        self,
        preset_id: int | None = None,
        error_message: str | None = None,
    ) -> str:
        """Return rendered gallery management partial HTML."""
        data = await self.get_gallery_for_ui(preset_id=preset_id)
        return self._presenter.render_gallery_html(data, error_message=error_message)

    async def get_photo_for_download(
        self, photo_id: int, session: Session | None = None
    ) -> dict[str, Any]:
        """Get photo with eager-loaded preset relationship for download."""
        with self._session_scope(session) as active_session:
            photo = self._repository.get_photo_with_preset(active_session, photo_id)

            if not photo:
                raise ValueError(f"Photo {photo_id} not found")

            preset_name = photo.preset.name if photo.preset else "Default"
            file_path = f"data/uploads/{preset_name}/{photo.filename}"

            return {
                "photo": photo,
                "preset_name": preset_name,
                "file_path": file_path,
            }

    async def get_photo_by_id(
        self, photo_id: int, session: Session | None = None
    ) -> PhotoDTO | None:
        """Get a photo by ID without eager-loading (for validation)."""
        with self._session_scope(session) as active_session:
            photo = self._repository.get_photo(active_session, photo_id)
            return self._photo_to_dto(photo) if photo else None

    async def get_image_payload(self, photo_id: int) -> dict[str, bytes]:
        """Resolve and validate file path, then return optimized image bytes."""
        photo_data = await self.get_photo_for_download(photo_id)
        photo = photo_data["photo"]
        preset_name = photo_data["preset_name"]
        file_path = self._upload_dir / preset_name / photo.filename

        # Enforce upload directory sandbox at the service boundary.
        if not file_path.resolve().is_relative_to(self._upload_dir.resolve()):
            raise PermissionError("Forbidden")
        if not file_path.exists():
            raise FileNotFoundError("File not found on disk")

        return {"bytes": self.optimize_path(file_path)}


def create_media_service(
    session_factory: SessionFactory,
    repository: IMediaRepository,
    storage: IMediaStorage,
    presenter: IMediaPresenter,
) -> IMediaService:
    """Factory that returns the media service implementation."""
    return MediaModuleService(session_factory, repository, storage, presenter)

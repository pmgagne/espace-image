"""Repository adapter for media module persistence."""

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.db.models import Photo, Preset
from app.modules.media.api.repositories import IMediaRepository


class MediaRepository(IMediaRepository):
    """SQLModel-backed repository for media use cases."""

    def create_preset(self, session: Session, name: str) -> Preset:
        """Create and persist a preset."""
        preset = Preset(name=name)
        session.add(preset)
        session.commit()
        session.refresh(preset)
        return preset

    def get_preset(self, session: Session, preset_id: int) -> Preset | None:
        """Return one preset by identifier."""
        return session.get(Preset, preset_id)

    def add_photo(self, session: Session, filename: str, preset_id: int) -> Photo:
        """Stage a photo row in the current session."""
        photo = Photo(filename=filename, preset_id=preset_id)
        session.add(photo)
        return photo

    def commit(self, session: Session) -> None:
        """Commit current transaction."""
        session.commit()

    def refresh_photo(self, session: Session, photo: Photo) -> None:
        """Refresh one photo row in-place."""
        session.refresh(photo)

    def get_photo(self, session: Session, photo_id: int) -> Photo | None:
        """Return one photo by identifier."""
        return session.get(Photo, photo_id)

    def delete_photo(self, session: Session, photo: Photo) -> None:
        """Delete one photo row."""
        session.delete(photo)

    def list_presets(self, session: Session) -> list[Preset]:
        """Return all presets."""
        return list(session.exec(select(Preset)).all())

    def list_photos_for_preset(self, session: Session, preset_id: int) -> list[Photo]:
        """Return all photos for one preset."""
        return list(session.exec(select(Photo).where(Photo.preset_id == preset_id)).all())

    def get_photo_with_preset(self, session: Session, photo_id: int) -> Photo | None:
        """Return one photo with eager-loaded preset relationship."""
        statement = select(Photo).where(Photo.id == photo_id).options(selectinload(Photo.preset))
        return session.exec(statement).first()

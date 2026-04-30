"""Repository helpers for slideshow module persistence reads."""

from sqlmodel import Session, select

from app.db.models import AppSettings, Photo


class SlideshowRepository:
    """Data access helper for slideshow selection."""

    def get_settings(self, session: Session) -> AppSettings | None:
        """Return current application settings if present."""
        return session.exec(select(AppSettings)).first()

    def list_photos_for_preset(self, session: Session, preset_id: int) -> list[Photo]:
        """Return photos associated with a preset."""
        return list(
            session.exec(select(Photo).where(Photo.preset_id == preset_id)).all()
        )

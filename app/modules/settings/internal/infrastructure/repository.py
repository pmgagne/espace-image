"""Repository helpers for settings module persistence."""

from sqlmodel import Session, func, select

from app.db.models import AppSettings, Photo, Preset


class SettingsRepository:
    """Data access helper for settings and presets."""

    def get_settings(self, session: Session) -> AppSettings | None:
        """Return first settings row if present."""
        return session.exec(select(AppSettings)).first()

    def list_presets(self, session: Session) -> list[tuple[Preset, int]]:
        """Return all presets paired with their photo count."""
        rows = session.exec(
            select(Preset, func.count(Photo.id))
            .join(Photo, Photo.preset_id == Preset.id, isouter=True)
            .group_by(Preset.id)
        ).all()
        return [(preset, count) for preset, count in rows]

    def get_preset(self, session: Session, preset_id: int) -> tuple[Preset, int] | None:
        """Return preset by id paired with its photo count."""
        preset = session.get(Preset, preset_id)
        if preset is None:
            return None
        count = session.exec(select(func.count(Photo.id)).where(Photo.preset_id == preset_id)).one()
        return preset, count

    def save(self, session: Session, settings: AppSettings) -> AppSettings:
        """Persist settings row."""
        session.add(settings)
        session.commit()
        return settings

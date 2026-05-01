"""Repository helpers for settings module persistence."""

from sqlmodel import Session, select

from app.db.models import AppSettings, Preset


class SettingsRepository:
    """Data access helper for settings and presets."""

    def get_settings(self, session: Session) -> AppSettings | None:
        """Return first settings row if present."""
        return session.exec(select(AppSettings)).first()

    def list_presets(self, session: Session) -> list[Preset]:
        """Return all presets."""
        return list(session.exec(select(Preset)).all())

    def get_preset(self, session: Session, preset_id: int) -> Preset | None:
        """Return preset by id."""
        return session.get(Preset, preset_id)

    def save(self, session: Session, settings: AppSettings) -> AppSettings:
        """Persist settings row."""
        session.add(settings)
        session.commit()
        return settings

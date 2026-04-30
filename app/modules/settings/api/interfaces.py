"""Public interfaces for the settings module."""

from typing import Protocol

from sqlmodel import Session

from app.db.models import AppSettings, Preset


class ISettingsService(Protocol):
    """Public interface for settings and preset access."""

    def get_settings(self, session: Session) -> AppSettings | None:
        """Return application settings or None when missing."""

    def list_presets(self, session: Session) -> list[Preset]:
        """Return all preset rows."""

    def get_preset(self, session: Session, preset_id: int) -> Preset | None:
        """Return a preset by identifier."""

    def save_settings(
        self,
        session: Session,
        active_preset_id: int | None,
        latitude: float | None,
        longitude: float | None,
        duration: int | None,
        default_alarm_for_all_events: bool,
    ) -> AppSettings:
        """Persist settings changes and return saved settings."""


def get_settings_service() -> ISettingsService:
    """Dependency injection token for settings service."""
    raise NotImplementedError("Settings service not initialized")

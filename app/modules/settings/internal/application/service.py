"""Settings module service implementation."""

from sqlmodel import Session

from app.db.models import AppSettings, Preset
from app.modules.settings.api.exceptions import PresetNotFoundError
from app.modules.settings.api.interfaces import ISettingsService
from app.modules.settings.internal.infrastructure.repository import SettingsRepository


class SettingsModuleService(ISettingsService):
    """Service exposing settings and preset operations."""

    def __init__(self, repository: SettingsRepository) -> None:
        """Initialize service with repository dependency."""
        self._repository = repository

    def get_settings(self, session: Session) -> AppSettings | None:
        """Return current settings if present."""
        return self._repository.get_settings(session)

    def list_presets(self, session: Session) -> list[Preset]:
        """Return all available presets."""
        return self._repository.list_presets(session)

    def get_preset(self, session: Session, preset_id: int) -> Preset | None:
        """Return a preset by id if found."""
        return self._repository.get_preset(session, preset_id)

    def save_settings(
        self,
        session: Session,
        active_preset_id: int | None,
        latitude: float | None,
        longitude: float | None,
        duration: int | None,
        default_alarm_for_all_events: bool,
    ) -> AppSettings:
        """Persist settings updates and return resulting row."""
        settings = self._repository.get_settings(session)
        if settings is None:
            settings = AppSettings()

        if active_preset_id is not None:
            preset = self._repository.get_preset(session, active_preset_id)
            if preset is None:
                raise PresetNotFoundError("Active preset not found")

        settings.active_preset_id = active_preset_id
        settings.weather_latitude = latitude
        settings.weather_longitude = longitude
        if duration is not None:
            settings.slideshow_duration = duration
        settings.default_alarm_for_all_events = default_alarm_for_all_events

        return self._repository.save(session, settings)


def create_settings_service() -> ISettingsService:
    """Factory that returns the settings service implementation."""
    return SettingsModuleService(SettingsRepository())

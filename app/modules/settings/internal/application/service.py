"""Settings module service implementation."""

from contextlib import contextmanager

from sqlmodel import Session

from app.db.models import AppSettings, Preset
from app.db.session_factory import SessionFactory
from app.modules.settings.api.contracts import AppSettingsDTO, PresetDTO
from app.modules.settings.api.exceptions import PresetNotFoundError
from app.modules.settings.api.interfaces import ISettingsService
from app.modules.settings.internal.infrastructure.repository import SettingsRepository


class SettingsModuleService(ISettingsService):
    """Service exposing settings and preset operations."""

    def __init__(self, repository: SettingsRepository, session_factory: SessionFactory) -> None:
        """Initialize service with repository and session factory dependencies."""
        self._repository = repository
        self._session_factory = session_factory

    @contextmanager
    def _session_scope(self, session: Session | None = None):
        """Yield provided session or create a new transactional session."""
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
    def _settings_to_dto(settings: AppSettings) -> AppSettingsDTO:
        """Convert AppSettings ORM to AppSettingsDTO."""
        return AppSettingsDTO(
            active_preset_id=settings.active_preset_id,
            weather_latitude=settings.weather_latitude,
            weather_longitude=settings.weather_longitude,
            slideshow_duration=settings.slideshow_duration,
            default_alarm_for_all_events=settings.default_alarm_for_all_events,
        )

    def get_settings(self, session: Session | None = None) -> AppSettingsDTO | None:
        """Return current settings if present."""
        with self._session_scope(session) as active_session:
            settings = self._repository.get_settings(active_session)
            return self._settings_to_dto(settings) if settings else None

    def list_presets(self, session: Session | None = None) -> list[PresetDTO]:
        """Return all available presets."""
        with self._session_scope(session) as active_session:
            presets = self._repository.list_presets(active_session)
            return [self._preset_to_dto(p) for p in presets]

    def get_preset(self, preset_id: int, session: Session | None = None) -> PresetDTO | None:
        """Return a preset by id if found."""
        with self._session_scope(session) as active_session:
            preset = self._repository.get_preset(active_session, preset_id)
            return self._preset_to_dto(preset) if preset else None

    def save_settings(
        self,
        active_preset_id: int | None,
        latitude: float | None,
        longitude: float | None,
        duration: int | None,
        default_alarm_for_all_events: bool,
        session: Session | None = None,
    ) -> AppSettingsDTO:
        """Persist settings updates and return resulting row."""
        with self._session_scope(session) as active_session:
            settings = self._repository.get_settings(active_session)
            if settings is None:
                settings = AppSettings()

            if active_preset_id is not None:
                preset = self._repository.get_preset(active_session, active_preset_id)
                if preset is None:
                    raise PresetNotFoundError("Active preset not found")

            settings.active_preset_id = active_preset_id
            settings.weather_latitude = latitude
            settings.weather_longitude = longitude
            if duration is not None:
                settings.slideshow_duration = duration
            settings.default_alarm_for_all_events = default_alarm_for_all_events

            saved_settings = self._repository.save(active_session, settings)
            return self._settings_to_dto(saved_settings)


def create_settings_service(session_factory: SessionFactory) -> ISettingsService:
    """Factory that returns the settings service implementation."""
    return SettingsModuleService(SettingsRepository(), session_factory)

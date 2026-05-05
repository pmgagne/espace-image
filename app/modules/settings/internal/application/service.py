"""Settings module service implementation."""

import math
from contextlib import contextmanager

from sqlmodel import Session

from app.db.models import AppSettings, Preset
from app.db.session_factory import SessionFactory
from app.modules.settings.api.contracts import AppSettingsDTO, PresetDTO, SettingsFormDTO
from app.modules.settings.api.exceptions import PresetNotFoundError
from app.modules.settings.api.interfaces import ISettingsService
from app.modules.settings.api.repositories import ISettingsRepository


class SettingsModuleService(ISettingsService):
    """Service exposing settings and preset operations."""

    def __init__(
        self,
        repository: ISettingsRepository,
        session_factory: SessionFactory,
    ) -> None:
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

    def get_settings_form(self) -> SettingsFormDTO:
        """Return settings form state with default-safe values for rendering."""
        current = self.get_settings()
        if current is None:
            return SettingsFormDTO(
                active_preset_id=None,
                weather_latitude=None,
                weather_longitude=None,
                slideshow_duration=30,
            )
        return SettingsFormDTO(
            active_preset_id=current.active_preset_id,
            weather_latitude=current.weather_latitude,
            weather_longitude=current.weather_longitude,
            slideshow_duration=current.slideshow_duration,
        )

    def with_location_preview(
        self,
        form: SettingsFormDTO,
        latitude: float,
        longitude: float,
    ) -> SettingsFormDTO:
        """Return a settings form state with preview coordinates applied."""
        return SettingsFormDTO(
            active_preset_id=form.active_preset_id,
            weather_latitude=latitude,
            weather_longitude=longitude,
            slideshow_duration=form.slideshow_duration,
        )

    def validate_settings_input(
        self,
        latitude: float | None,
        longitude: float | None,
        duration: int | None,
    ) -> None:
        """Validate settings form inputs and raise ValueError when invalid."""
        if latitude is not None and (
            math.isnan(latitude) or math.isinf(latitude) or not (-90.0 <= latitude <= 90.0)
        ):
            raise ValueError("Invalid latitude value")
        if longitude is not None and (
            math.isnan(longitude) or math.isinf(longitude) or not (-180.0 <= longitude <= 180.0)
        ):
            raise ValueError("Invalid longitude value")
        if duration is not None and duration <= 0:
            raise ValueError("Duration must be a positive integer")


def create_settings_service(
    session_factory: SessionFactory,
    repository: ISettingsRepository,
) -> ISettingsService:
    """Factory that returns the settings service implementation."""
    return SettingsModuleService(repository, session_factory)

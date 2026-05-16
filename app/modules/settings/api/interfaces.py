"""Public interfaces for the settings module."""

from typing import Protocol

from app.modules.settings.api.contracts import AppSettingsDTO, PresetDTO, SettingsFormDTO


class ISettingsService(Protocol):
    """Public interface for settings and preset access."""

    def get_settings(self) -> AppSettingsDTO | None:
        """Return application settings or None when missing."""
        ...

    def list_presets(self) -> list[PresetDTO]:
        """Return all preset rows."""
        ...

    def get_preset(self, preset_id: int) -> PresetDTO | None:
        """Return a preset by identifier."""
        ...

    def save_settings(
        self,
        active_preset_id: int | None,
        latitude: float | None,
        longitude: float | None,
        duration: int | None,
    ) -> AppSettingsDTO:
        """Persist settings changes and return saved settings."""
        ...

    def get_settings_form(self) -> SettingsFormDTO:
        """Return settings form state with default-safe values for rendering."""
        ...

    def with_location_preview(
        self,
        form: SettingsFormDTO,
        latitude: float,
        longitude: float,
    ) -> SettingsFormDTO:
        """Return a settings form state with preview coordinates applied."""
        ...

    def validate_settings_input(
        self,
        latitude: float | None,
        longitude: float | None,
        duration: int | None,
    ) -> None:
        """Validate settings form inputs and raise ValueError when invalid."""
        ...


def get_settings_service() -> ISettingsService:
    """Dependency injection token for settings service."""
    raise NotImplementedError("Settings service not initialized")

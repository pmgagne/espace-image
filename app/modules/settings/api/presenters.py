"""Presenter ports for settings module."""

from typing import Protocol

from app.modules.settings.api.contracts import PresetDTO, SettingsFormDTO


class ISettingsPresenter(Protocol):
    """Presentation port for settings HTML rendering."""

    def render_settings_html(
        self,
        settings: SettingsFormDTO,
        presets: list[PresetDTO],
        location_name: str | None,
        backend_timezone: str,
    ) -> str:
        """Render settings partial HTML."""
        ...

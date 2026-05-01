"""Presenter adapter for settings HTML rendering."""

from app.modules.settings.api.contracts import PresetDTO, SettingsFormDTO
from app.modules.settings.api.presenters import ISettingsPresenter
from app.template_config import templates


class SettingsPresenter(ISettingsPresenter):
    """Template-backed presenter for settings partials."""

    def render_settings_html(
        self,
        settings: SettingsFormDTO,
        presets: list[PresetDTO],
        location_name: str | None,
        backend_timezone: str,
    ) -> str:
        """Render settings partial HTML."""
        tpl = templates.env.get_template("partials/settings.html")
        return tpl.render(
            settings=settings,
            presets=presets,
            location_name=location_name,
            backend_timezone=backend_timezone,
        )

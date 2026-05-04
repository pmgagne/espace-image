"""GUI presenter adapter for settings module.

Provides helper to render the settings partial used by admin routers.
"""

from app.template_config import templates
from app.utils.timezone import get_local_timezone_name


def render_settings_fragment(settings_form, presets, location_name: str | None) -> str:
    """Render the settings HTML fragment.

    Args:
        settings_form: Settings form data (as returned by settings service).
        presets: List of presets for the UI.
        location_name: Optional human-readable location preview.

    Returns:
        Rendered HTML string for the settings partial.
    """
    tpl = templates.env.get_template("partials/settings.html")
    return tpl.render(
        settings=settings_form,
        presets=presets,
        location_name=location_name,
        backend_timezone=get_local_timezone_name(),
    )

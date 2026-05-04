"""GUI presenter adapter for weather module."""

from app.template_config import templates


def render_weather_fragment(*, has_location: bool, weather: dict | None = None) -> str:
    """Render the weather component fragment.

    Args:
        has_location: Whether weather coordinates are configured.
        weather: Optional weather payload for display.

    Returns:
        Rendered HTML string for the weather partial.
    """
    tpl = templates.env.get_template("partials/weather.html")
    if not has_location:
        return tpl.render(has_location=False)
    return tpl.render(has_location=True, weather=weather or {})

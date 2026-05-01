"""Presenter adapter for weather HTML rendering."""

from typing import Any

from app.modules.weather.api.presenters import IWeatherPresenter
from app.template_config import templates


class WeatherPresenter(IWeatherPresenter):
    """Template-backed presenter for weather partials."""

    def render_weather_html(
        self,
        has_location: bool,
        weather: dict[str, Any] | None = None,
    ) -> str:
        """Render weather widget HTML fragment."""
        tpl = templates.env.get_template("partials/weather.html")
        if not has_location:
            return tpl.render(has_location=False)
        return tpl.render(has_location=True, weather=weather or {})

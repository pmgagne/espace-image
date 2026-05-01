"""Presenter ports for weather module."""

from typing import Any, Protocol


class IWeatherPresenter(Protocol):
    """Presentation port for weather HTML rendering."""

    def render_weather_html(
        self,
        has_location: bool,
        weather: dict[str, Any] | None = None,
    ) -> str:
        """Render weather widget HTML fragment."""
        ...

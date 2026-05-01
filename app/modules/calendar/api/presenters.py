"""Presenter ports for calendar module."""

from typing import Any, Protocol


class ICalendarPresenter(Protocol):
    """Presentation port for calendar HTML rendering."""

    def render_calendars_html(self, data: dict[str, Any]) -> str:
        """Render calendar management partial HTML."""
        ...

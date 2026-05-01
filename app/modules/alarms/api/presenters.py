"""Presenter ports for alarms module."""

from typing import Any, Protocol


class IAlarmsPresenter(Protocol):
    """Presentation port for alarm HTML rendering."""

    def render_alarm_html(self, alarm_contexts: list[dict[str, Any]]) -> str:
        """Render alarm contexts into HTML fragment."""
        ...

    def render_debug_html(self, success_message: str | None = None) -> str:
        """Render debug panel HTML fragment."""
        ...

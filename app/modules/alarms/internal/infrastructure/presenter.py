"""Presenter adapter for alarms module HTML rendering."""

from typing import Any

from app.modules.alarms.api.presenters import IAlarmsPresenter
from app.template_config import templates


class AlarmsPresenter(IAlarmsPresenter):
    """Template-backed presenter for alarm partials."""

    def render_alarm_html(self, alarm_contexts: list[dict[str, Any]]) -> str:
        """Render alarm contexts into HTML fragment."""
        if not alarm_contexts:
            return ""
        tpl = templates.env.get_template("partials/alarms.html")
        return tpl.render(alarms=alarm_contexts)

    def render_debug_html(self, success_message: str | None = None) -> str:
        """Render debug panel HTML fragment."""
        tpl = templates.env.get_template("partials/debug.html")
        if success_message:
            return tpl.render(success_message=success_message)
        return tpl.render()

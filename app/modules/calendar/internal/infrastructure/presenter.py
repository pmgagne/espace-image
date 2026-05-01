"""Presenter adapter for calendar HTML rendering."""

from typing import Any

from app.modules.calendar.api.presenters import ICalendarPresenter
from app.template_config import templates


class CalendarPresenter(ICalendarPresenter):
    """Template-backed presenter for calendar management partials."""

    def render_calendars_html(self, data: dict[str, Any]) -> str:
        """Render calendar management partial HTML."""
        tpl = templates.env.get_template("partials/calendars.html")
        return tpl.render(**data)

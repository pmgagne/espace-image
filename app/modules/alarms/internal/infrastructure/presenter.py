"""GUI presenter adapter for alarms module.

This file lives in the module's infrastructure layer and is intended to be
used only by GUI routers to render HTML fragments for alarms. It keeps
template rendering out of the application service layer.
"""

from __future__ import annotations

from app.template_config import templates


def render_alarms_fragment(alarms: list[dict]) -> str:
    """Render the alarms HTML fragment used by the GUI.

    Args:
        alarms: List of alarm context dictionaries as returned by the
            `IAlarmsService.get_alarm_contexts` call.

    Returns:
        Rendered HTML string for the alarms partial.
    """
    tpl = templates.env.get_template("partials/alarms.html")
    return tpl.render(alarms=alarms)


def render_debug_fragment(success_message: str | None = None) -> str:
    """Render the debug panel HTML fragment used by admin GUI routes.

    Args:
        success_message: Optional success message for debug actions.

    Returns:
        Rendered HTML string for the debug partial.
    """
    tpl = templates.env.get_template("partials/debug.html")
    return tpl.render(success_message=success_message)

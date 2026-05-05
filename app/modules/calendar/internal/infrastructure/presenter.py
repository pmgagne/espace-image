"""GUI presenter adapter for calendar module."""

from app.template_config import templates


def render_calendars_fragment(data: dict) -> str:
    """Render the calendars component fragment.

    Args:
        data: Calendar UI payload from `get_calendars_for_ui`.

    Returns:
        Rendered HTML string for the calendars partial.
    """
    tpl = templates.env.get_template("partials/calendars.html")
    return tpl.render(**data)

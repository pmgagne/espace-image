"""GUI presenter adapter for media module.

Provides helper to render the gallery partial used by admin routers.
"""

from app.template_config import templates


def render_gallery_fragment(data: dict, error_message: str | None = None) -> str:
    """Render the gallery HTML fragment.

    Args:
        data: Context dictionary returned by `IMediaService.get_gallery_for_ui`.
        error_message: Optional error message to display in the fragment.

    Returns:
        Rendered HTML string for the gallery partial.
    """
    tpl = templates.env.get_template("partials/gallery.html")
    return tpl.render(**data, error_message=error_message)

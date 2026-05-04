"""GUI presenter adapter for slideshow module."""

from app.template_config import templates


def render_slide_fragment(*, img_url: str | None, error_msg: str | None) -> str:
    """Render the slideshow component fragment.

    Args:
        img_url: Optional URL for the selected slide image.
        error_msg: Optional error message when no slide is available.

    Returns:
        Rendered HTML string for the slide partial.
    """
    tpl = templates.env.get_template("partials/slide.html")
    if error_msg:
        return tpl.render(error_msg=error_msg)
    return tpl.render(img_url=img_url)

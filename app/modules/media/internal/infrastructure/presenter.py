"""Presenter adapter for media HTML rendering."""

from typing import Any

from app.modules.media.api.presenters import IMediaPresenter
from app.template_config import templates


class MediaPresenter(IMediaPresenter):
    """Template-backed presenter for media gallery partials."""

    def render_gallery_html(
        self,
        data: dict[str, Any],
        error_message: str | None = None,
    ) -> str:
        """Render gallery management partial HTML."""
        tpl = templates.env.get_template("partials/gallery.html")
        if error_message:
            return tpl.render(**data, error_message=error_message)
        return tpl.render(**data)

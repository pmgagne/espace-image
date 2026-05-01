"""Presenter adapter for slideshow HTML rendering."""

from app.modules.slideshow.api.interfaces import SlideSelectionResult
from app.modules.slideshow.api.presenters import ISlideshowPresenter
from app.template_config import templates


class SlideshowPresenter(ISlideshowPresenter):
    """Template-backed presenter for slideshow partials."""

    def render_slide_html(self, selection: SlideSelectionResult) -> str:
        """Render slideshow selection into HTML fragment."""
        tpl = templates.env.get_template("partials/slide.html")
        if selection.error_msg:
            return tpl.render(error_msg=selection.error_msg)
        return tpl.render(img_url=selection.img_url)

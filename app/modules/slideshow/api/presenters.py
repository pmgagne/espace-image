"""Presenter ports for slideshow module."""

from typing import Protocol

from app.modules.slideshow.api.interfaces import SlideSelectionResult


class ISlideshowPresenter(Protocol):
    """Presentation port for slide HTML rendering."""

    def render_slide_html(self, selection: SlideSelectionResult) -> str:
        """Render slideshow selection into HTML fragment."""
        ...

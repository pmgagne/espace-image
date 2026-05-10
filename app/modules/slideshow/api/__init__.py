"""Public slideshow module API."""

from app.modules.slideshow.internal.infrastructure.presenter import render_slide_fragment

from .interfaces import ISlideshowService, SlideSelectionResult, get_slideshow_service

__all__ = [
    "ISlideshowService",
    "SlideSelectionResult",
    "get_slideshow_service",
    "render_slide_fragment",
]

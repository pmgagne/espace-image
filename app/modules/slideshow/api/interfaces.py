"""Public interfaces for the slideshow module."""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class SlideSelectionResult:
    """Result for selecting next slideshow image."""

    img_url: str | None
    error_msg: str | None


class ISlideshowService(Protocol):
    """Public interface for slideshow selection operations."""

    def select_next_slide(self, mode: str = "modern") -> SlideSelectionResult:
        """Return next slide URL or an error message."""

    async def get_slide_html(self, mode: str = "modern") -> str:
        """Get rendered HTML for slide component."""
        ...


def get_slideshow_service() -> ISlideshowService:
    """Dependency injection token for slideshow service."""
    raise NotImplementedError("Slideshow service not initialized")

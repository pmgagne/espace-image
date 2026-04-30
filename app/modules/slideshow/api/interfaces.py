"""Public interfaces for the slideshow module."""

from dataclasses import dataclass
from typing import Protocol

from sqlmodel import Session


@dataclass
class SlideSelectionResult:
    """Result for selecting next slideshow image."""

    img_url: str | None
    error_msg: str | None


class ISlideshowService(Protocol):
    """Public interface for slideshow selection operations."""

    def select_next_slide(
        self, session: Session, mode: str = "modern"
    ) -> SlideSelectionResult:
        """Return next slide URL or an error message."""


def get_slideshow_service() -> ISlideshowService:
    """Dependency injection token for slideshow service."""
    raise NotImplementedError("Slideshow service not initialized")

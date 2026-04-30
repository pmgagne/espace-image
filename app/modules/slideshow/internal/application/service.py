"""Slideshow module service implementation."""

import random

from sqlmodel import Session

from app.modules.slideshow.api.interfaces import ISlideshowService, SlideSelectionResult
from app.modules.slideshow.internal.infrastructure.repository import SlideshowRepository


class SlideshowModuleService(ISlideshowService):
    """Service exposing slideshow selection operations."""

    def __init__(self, repository: SlideshowRepository) -> None:
        """Initialize service with repository dependency."""
        self._repository = repository

    def select_next_slide(
        self, session: Session, mode: str = "modern"
    ) -> SlideSelectionResult:
        """Return next slide URL or error message for slideshow rendering."""
        settings = self._repository.get_settings(session)
        if settings is None or settings.active_preset_id is None:
            return SlideSelectionResult(
                img_url=None,
                error_msg="No Preset Active. Please configure in Admin.",
            )

        photos = self._repository.list_photos_for_preset(
            session, settings.active_preset_id
        )
        if not photos:
            return SlideSelectionResult(
                img_url=None,
                error_msg="No Photos found in the active preset.",
            )

        photo = random.choice(photos)
        return SlideSelectionResult(
            img_url=f"/images/{photo.id}?mode={mode}", error_msg=None
        )


def create_slideshow_service() -> ISlideshowService:
    """Factory that returns the slideshow service implementation."""
    return SlideshowModuleService(SlideshowRepository())

"""Slideshow module service implementation."""

import random
from contextlib import contextmanager

from sqlmodel import Session

from app.db.session_factory import SessionFactory
from app.modules.slideshow.api.interfaces import ISlideshowService, SlideSelectionResult
from app.modules.slideshow.internal.infrastructure.repository import SlideshowRepository


class SlideshowModuleService(ISlideshowService):
    """Service exposing slideshow selection operations."""

    def __init__(self, repository: SlideshowRepository, session_factory: SessionFactory) -> None:
        """Initialize service with repository and session factory dependencies."""
        self._repository = repository
        self._session_factory = session_factory

    @contextmanager
    def _session_scope(self, session: Session | None = None):
        """Yield provided session or create a local DB session."""
        if session is not None:
            yield session
            return
        with self._session_factory.session_scope() as local_session:
            yield local_session

    def select_next_slide(
        self,
        mode: str = "modern",
        session: Session | None = None,
    ) -> SlideSelectionResult:
        """Return next slide URL or error message for slideshow rendering."""
        with self._session_scope(session) as active_session:
            settings = self._repository.get_settings(active_session)
            if settings is None or settings.active_preset_id is None:
                return SlideSelectionResult(
                    img_url=None,
                    error_msg="No Preset Active. Please configure in Admin.",
                )

            photos = self._repository.list_photos_for_preset(
                active_session,
                settings.active_preset_id,
            )
            if not photos:
                return SlideSelectionResult(
                    img_url=None,
                    error_msg="No Photos found in the active preset.",
                )

            photo = random.choice(photos)
            return SlideSelectionResult(img_url=f"/images/{photo.id}?mode={mode}", error_msg=None)

    async def get_slide_html(self, mode: str = "modern") -> str:
        """
        Get rendered HTML for slide component.

        Returns HTML fragment with either slide image or error message.
        """
        from app.template_config import templates

        selection = self.select_next_slide(mode)
        tpl = templates.env.get_template("partials/slide.html")

        if selection.error_msg:
            return tpl.render(error_msg=selection.error_msg)

        return tpl.render(img_url=selection.img_url)


def create_slideshow_service(session_factory: SessionFactory) -> ISlideshowService:
    """Factory that returns the slideshow service implementation."""
    return SlideshowModuleService(SlideshowRepository(), session_factory)

"""Slideshow module dependency wiring."""

from fastapi import FastAPI

from app.db.engine import engine
from app.db.session_factory import SessionFactory

from .api.interfaces import get_slideshow_service
from .internal.application.service import create_slideshow_service
from .internal.infrastructure.repository import SlideshowRepository


async def init(app: FastAPI) -> None:
    """Initialize slideshow module dependencies."""
    session_factory = SessionFactory(engine)
    service = create_slideshow_service(
        session_factory,
        SlideshowRepository(),
    )
    app.dependency_overrides[get_slideshow_service] = lambda: service


def post_init(_app: FastAPI) -> None:
    """Run post-initialization hooks for slideshow module."""


async def teardown(_app: FastAPI) -> None:
    """Run teardown hooks for slideshow module."""

"""Slideshow module dependency wiring."""

from fastapi import FastAPI

from .api.interfaces import get_slideshow_service
from .internal.application.service import create_slideshow_service


async def init(app: FastAPI) -> None:
    """Initialize slideshow module dependencies."""
    service = create_slideshow_service()
    app.dependency_overrides[get_slideshow_service] = lambda: service


def post_init(_app: FastAPI) -> None:
    """Run post-initialization hooks for slideshow module."""


async def teardown(_app: FastAPI) -> None:
    """Run teardown hooks for slideshow module."""

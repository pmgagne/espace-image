"""Media module dependency wiring."""

from fastapi import FastAPI

from .api.interfaces import get_media_service
from .internal.application.service import create_media_service


async def init(app: FastAPI) -> None:
    """Initialize media module dependencies."""
    service = create_media_service()
    app.dependency_overrides[get_media_service] = lambda: service


def post_init(_app: FastAPI) -> None:
    """Run post-initialization hooks for media module."""


async def teardown(_app: FastAPI) -> None:
    """Run teardown hooks for media module."""

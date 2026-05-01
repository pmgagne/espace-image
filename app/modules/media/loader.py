"""Media module dependency wiring."""

from fastapi import FastAPI

from app.db.engine import engine
from app.db.session_factory import SessionFactory

from .api.interfaces import get_media_service
from .internal.application.service import create_media_service
from .internal.infrastructure.image_ops import GalleryManager
from .internal.infrastructure.presenter import MediaPresenter
from .internal.infrastructure.repository import MediaRepository


async def init(app: FastAPI) -> None:
    """Initialize media module dependencies."""
    session_factory = SessionFactory(engine)
    service = create_media_service(
        session_factory,
        MediaRepository(),
        GalleryManager(),
        MediaPresenter(),
    )
    app.dependency_overrides[get_media_service] = lambda: service


def post_init(_app: FastAPI) -> None:
    """Run post-initialization hooks for media module."""


async def teardown(_app: FastAPI) -> None:
    """Run teardown hooks for media module."""

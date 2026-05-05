"""Settings module dependency wiring."""

from fastapi import FastAPI

from app.db.engine import engine
from app.db.session_factory import SessionFactory

from .api.interfaces import get_settings_service
from .internal.application.service import create_settings_service
from .internal.infrastructure.repository import SettingsRepository


async def init(app: FastAPI) -> None:
    """Initialize settings module dependencies."""
    session_factory = SessionFactory(engine)
    service = create_settings_service(
        session_factory,
        SettingsRepository(),
    )
    app.dependency_overrides[get_settings_service] = lambda: service


def post_init(_app: FastAPI) -> None:
    """Run post-initialization hooks for settings module."""


async def teardown(_app: FastAPI) -> None:
    """Run teardown hooks for settings module."""

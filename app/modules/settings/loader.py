"""Settings module dependency wiring."""

from typing import Any

from .api.interfaces import get_settings_service
from .internal.application.service import create_settings_service


async def init(app: Any) -> None:
    """Initialize settings module dependencies."""
    service = create_settings_service()
    app.dependency_overrides[get_settings_service] = lambda: service


def post_init(_app: Any) -> None:
    """Run post-initialization hooks for settings module."""


async def teardown(_app: Any) -> None:
    """Run teardown hooks for settings module."""

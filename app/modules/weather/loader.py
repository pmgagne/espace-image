"""Weather module dependency wiring."""

from fastapi import FastAPI

from .api.interfaces import get_weather_service
from .internal.application.service import create_weather_service


async def init(app: FastAPI) -> None:
    """Initialize weather module dependencies."""
    service = create_weather_service()
    app.dependency_overrides[get_weather_service] = lambda: service


def post_init(_app: FastAPI) -> None:
    """Run post-initialization hooks for weather module."""


async def teardown(_app: FastAPI) -> None:
    """Run teardown hooks for weather module."""

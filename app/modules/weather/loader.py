"""Weather module dependency wiring."""

from fastapi import FastAPI

from app.db.engine import engine
from app.db.session_factory import SessionFactory

from .api.interfaces import get_weather_service
from .internal.application.service import create_weather_service
from .internal.infrastructure.gateway import WeatherGateway


async def init(app: FastAPI) -> None:
    """Initialize weather module dependencies."""
    session_factory = SessionFactory(engine)
    service = create_weather_service(
        session_factory,
        WeatherGateway(),
    )
    app.dependency_overrides[get_weather_service] = lambda: service


def post_init(_app: FastAPI) -> None:
    """Run post-initialization hooks for weather module."""


async def teardown(_app: FastAPI) -> None:
    """Run teardown hooks for weather module."""

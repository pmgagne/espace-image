"""Calendar module dependency wiring."""

import logging

from fastapi import FastAPI

from app.db.engine import engine
from app.db.session_factory import SessionFactory

from .api.interfaces import get_calendar_service
from .internal.application.service import create_calendar_service

logger = logging.getLogger(__name__)


async def init(app: FastAPI) -> None:
    """Initialize calendar module dependencies."""
    session_factory = SessionFactory(engine)
    service = create_calendar_service(session_factory)
    app.dependency_overrides[get_calendar_service] = lambda: service
    logger.info("Initialized calendar module")


def post_init(_app: FastAPI) -> None:
    """Run post-initialization hooks for calendar module."""


async def teardown(_app: FastAPI) -> None:
    """Run teardown hooks for calendar module."""
    logger.info("Tearing down calendar module")

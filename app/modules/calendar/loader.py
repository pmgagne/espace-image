"""Calendar module dependency wiring."""

import logging
from typing import Any

from .api.interfaces import get_calendar_service
from .internal.application.service import create_calendar_service

logger = logging.getLogger(__name__)


async def init(app: Any) -> None:
    """Initialize calendar module dependencies."""
    service = create_calendar_service()
    app.dependency_overrides[get_calendar_service] = lambda: service
    logger.info("Initialized calendar module")


def post_init(_app: Any) -> None:
    """Run post-initialization hooks for calendar module."""


async def teardown(_app: Any) -> None:
    """Run teardown hooks for calendar module."""
    logger.info("Tearing down calendar module")

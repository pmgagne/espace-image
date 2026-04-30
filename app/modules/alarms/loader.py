"""Alarms module dependency wiring."""

import logging
from typing import Any

from .api.interfaces import get_alarms_service
from .internal.application.service import create_alarms_service

logger = logging.getLogger(__name__)


async def init(app: Any) -> None:
    """Initialize alarms module dependencies."""
    service = create_alarms_service()
    app.dependency_overrides[get_alarms_service] = lambda: service
    logger.info("Initialized alarms module")


def post_init(_app: Any) -> None:
    """Run post-initialization hooks for alarms module."""


async def teardown(_app: Any) -> None:
    """Run teardown hooks for alarms module."""
    logger.info("Tearing down alarms module")

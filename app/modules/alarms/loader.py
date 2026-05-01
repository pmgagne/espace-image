"""Alarms module dependency wiring."""

import logging

from fastapi import FastAPI

from .api.interfaces import get_alarms_service
from .internal.application.service import create_alarms_service

logger = logging.getLogger(__name__)


async def init(app: FastAPI) -> None:
    """Initialize alarms module dependencies."""
    service = create_alarms_service()
    app.dependency_overrides[get_alarms_service] = lambda: service
    logger.info("Initialized alarms module")


def post_init(_app: FastAPI) -> None:
    """Run post-initialization hooks for alarms module."""


async def teardown(_app: FastAPI) -> None:
    """Run teardown hooks for alarms module."""
    logger.info("Tearing down alarms module")

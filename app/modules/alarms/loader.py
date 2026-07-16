"""Alarms module dependency wiring."""

import logging

from fastapi import FastAPI

from app.db.engine import engine
from app.db.session_factory import SessionFactory

from .api.interfaces import IAlarmsService, get_alarms_service
from .internal.application.service import create_alarms_service
from .internal.infrastructure.repository import AlarmsRepository

logger = logging.getLogger(__name__)


def build_alarms_service(session_factory: SessionFactory) -> IAlarmsService:
    """Module-owned composition helper for the alarms service.

    Mirrors `app.modules.calendar.loader.build_calendar_service` so callers
    outside the module (e.g. the APScheduler background job in
    `app/main.py`) never need to import from `internal/`.
    """
    return create_alarms_service(session_factory, AlarmsRepository())


async def init(app: FastAPI) -> None:
    """Initialize alarms module dependencies."""
    session_factory = SessionFactory(engine)
    service = build_alarms_service(session_factory)
    app.dependency_overrides[get_alarms_service] = lambda: service
    logger.info("Initialized alarms module")


def post_init(_app: FastAPI) -> None:
    """Run post-initialization hooks for alarms module."""


async def teardown(_app: FastAPI) -> None:
    """Run teardown hooks for alarms module."""
    logger.info("Tearing down alarms module")

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# Import configuration constants
from app.config import CALENDAR_SYNC_INTERVAL_MINUTES
from app.db.engine import create_db_and_tables
from app.db.session_factory import SessionFactory
from app.modules.calendar.internal.application.service import (
    create_calendar_service,
)
from app.modules.loader import app_init, app_post_init, app_teardown
from app.routers import admin, dashboard, media

# Security Note: This application has NO authentication and is designed for
# internal-network-only deployment. See SECURITY.md for details.

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response


async def background_sync_calendars() -> None:
    """Background task to sync calendar events on configured interval."""
    try:
        # Create calendar service directly (outside FastAPI DI context)
        from app.db.engine import engine

        session_factory = SessionFactory(engine)
        calendar_service = create_calendar_service(session_factory)
        await calendar_service.sync_calendars()
    except Exception as e:
        logger.exception("Error in background calendar sync: %s", e)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Startup
    create_db_and_tables()
    await app_init(_app)
    logger.info("Application startup (LOG_LEVEL=%s)", LOG_LEVEL)

    # Sync calendars on startup
    logger.info("Performing initial calendar sync on startup")
    try:
        await background_sync_calendars()
        logger.info("Initial calendar sync completed successfully")
    except Exception as e:
        logger.error("Initial calendar sync failed: %s", e)

    # Start the APScheduler
    scheduler.add_job(
        background_sync_calendars,
        "interval",
        minutes=CALENDAR_SYNC_INTERVAL_MINUTES,
        id="calendar_sync",
        name=f"Sync calendar events every {CALENDAR_SYNC_INTERVAL_MINUTES} minutes",
        next_run_time=datetime.now(UTC),
    )
    scheduler.start()
    logger.info(
        "Scheduler started (calendar sync every %s minutes)",
        CALENDAR_SYNC_INTERVAL_MINUTES,
    )

    yield

    # Shutdown
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shutdown complete")
    await app_teardown(_app)


app = FastAPI(title="Espace-Image", lifespan=lifespan)
app_post_init(app)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Ensure static directory exists
os.makedirs("app/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Import centralized template configuration with all globals

# Include Routers
app.include_router(dashboard.router)
app.include_router(media.router)
app.include_router(admin.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}

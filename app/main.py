import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session
from starlette.middleware.base import BaseHTTPMiddleware

# Import configuration constants
from app.config import CALENDAR_SYNC_INTERVAL_MINUTES
from app.db.engine import create_db_and_tables, engine
from app.routers import admin, dashboard, media
from app.services.calendar_service import CalendarService

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

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response


async def background_sync_calendars():
    """Background task to sync calendar events on configured interval."""
    with Session(engine) as session:
        try:
            await CalendarService.sync_calendar_events(session)
        except Exception as e:
            logger.exception("Error in background calendar sync: %s", e)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    create_db_and_tables()
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
        "Scheduler started (calendar sync every %s minutes)", CALENDAR_SYNC_INTERVAL_MINUTES
    )

    yield

    # Shutdown
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shutdown complete")


app = FastAPI(title="Espace-Image", lifespan=lifespan)

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
async def health_check():
    return {"status": "ok"}

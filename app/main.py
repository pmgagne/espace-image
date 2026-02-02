import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from app.db.engine import create_db_and_tables, engine
from app.routers import admin, dashboard, media
from app.services.calendar_service import CalendarService

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.WARNING))
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def background_sync_calendars():
    """Background task to sync calendar events every 10 minutes."""
    session = Session(engine)
    try:
        await CalendarService.sync_calendar_events(session)
    except Exception as e:
        logger.exception(f"Error in background calendar sync: {e}")
    finally:
        session.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    create_db_and_tables()

    # Start the APScheduler
    scheduler.add_job(
        background_sync_calendars,
        "interval",
        minutes=10,
        id="calendar_sync",
        name="Sync calendar events every 10 minutes",
        next_run_time=datetime.now(),
    )
    scheduler.start()

    yield

    # Shutdown
    if scheduler.running:
        scheduler.shutdown()


app = FastAPI(title="Espace-Image", lifespan=lifespan)

# Ensure static directory exists
os.makedirs("app/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

# Debug mode flag
DEBUG_MODE = os.getenv("WEBAPP_DEBUG", "").lower() in ("true", "1", "yes")
templates.env.globals["debug_mode"] = DEBUG_MODE

# Include Routers
app.include_router(dashboard.router)
app.include_router(media.router)
app.include_router(admin.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}

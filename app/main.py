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
from app.config import BACKGROUND_SYNC_DEFAULT_MINUTES
from app.db.session_factory import SessionFactory
from app.modules.alarms.rest import router as alarms_rest_router
from app.modules.calendar.loader import build_calendar_service
from app.modules.calendar.rest import router as calendar_rest_router
from app.modules.loader import app_init, app_post_init, app_teardown
from app.modules.media.rest import router as media_rest_router
from app.modules.settings.rest import router as settings_rest_router
from app.modules.slideshow.rest import router as slideshow_rest_router
from app.modules.weather.rest import router as weather_rest_router
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


# Filter to sanitize APScheduler Job objects in log records so their
# stringification doesn't include trigger/next-run details.
class _SanitizeApschedulerJobFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        args = getattr(record, "args", None)
        if not args:
            return True
        try:
            new_args = list(args)
        except Exception:
            return True
        changed = False
        for i, a in enumerate(new_args):
            try:
                # Detect APScheduler Job-like objects and replace with their
                # `name` so the logger message does not include trigger info.
                if (
                    hasattr(a, "__class__")
                    and a.__class__.__module__.startswith("apscheduler")
                    and hasattr(a, "name")
                ):
                    new_args[i] = a.name
                    changed = True
            except Exception:
                continue
        if changed:
            record.args = tuple(new_args)
        return True


# Attach the filter to the APScheduler executor logger so job objects are
# sanitized before message formatting.
logging.getLogger("apscheduler.executors.default").addFilter(_SanitizeApschedulerJobFilter())

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
        # Build calendar service via module-owned composition helper
        from app.db.engine import engine

        session_factory = SessionFactory(engine)
        calendar_service = build_calendar_service(session_factory)
        # If the calendar service exposes `get_calendars_for_ui`, use it to
        # detect an empty configuration and skip sync when there are no sources.
        # Otherwise (e.g., in tests or older service implementations), run sync.
        should_skip = False
        if hasattr(calendar_service, "get_calendars_for_ui"):
            try:
                ui = await calendar_service.get_calendars_for_ui()
                sources = ui.get("sources", []) if isinstance(ui, dict) else []
            except Exception:
                sources = []

            if not sources:
                should_skip = True

        if should_skip:
            logger.info("Background calendar sync skipped: no calendar sources configured")
            return

        result = await calendar_service.general_sync()
        if result.alarms_skipped:
            logger.info(
                "Background general sync skipped alarm normalization: %s",
                result.alarms_skip_reason,
            )
        else:
            logger.info(
                "Background general sync normalized %s alarm occurrences",
                result.normalized_alarm_count,
            )

        # Purge stale past alarm/event rows so the AlarmEvent table stays bounded.
        try:
            from app.modules.alarms.internal.application.service import create_alarms_service
            from app.modules.alarms.internal.infrastructure.repository import AlarmsRepository

            alarms_service = create_alarms_service(session_factory, AlarmsRepository())
            purged = await alarms_service.purge_old_alarms()
            logger.info("Background sync purged %s old alarm rows", purged)
        except Exception:
            logger.exception("Error purging old alarms during background sync")
    except Exception as e:
        logger.exception("Error in background calendar sync: %s", e)


def _sync_period_minutes() -> float:
    return float(BACKGROUND_SYNC_DEFAULT_MINUTES)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Startup
    await app_init(_app)
    logger.info("Application startup (LOG_LEVEL=%s)", LOG_LEVEL)

    # Start APScheduler and register a periodic sync job.
    # max_instances=1 prevents overlapping runs.
    # coalesce=True collapses backlog/misfires to a single execution.
    scheduler.start()
    logger.info("Scheduler started")

    sync_period_minutes = _sync_period_minutes()
    scheduler.add_job(
        background_sync_calendars,
        "interval",
        minutes=sync_period_minutes,
        id="calendar_sync",
        name="Periodic calendar sync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=max(int(sync_period_minutes * 60), 60),
        next_run_time=datetime.now(UTC),
    )
    logger.info(
        "Scheduled periodic calendar sync every %.1f minutes (max_instances=1)",
        sync_period_minutes,
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
app.include_router(alarms_rest_router)
app.include_router(calendar_rest_router)
app.include_router(media_rest_router)
app.include_router(settings_rest_router)
app.include_router(weather_rest_router)
app.include_router(slideshow_rest_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}

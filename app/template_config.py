"""Centralized Jinja2 template configuration.

This module provides a single Jinja2Templates instance with all global variables
configured. This ensures template globals are consistently available across all routers.
"""

import os

from fastapi.templating import Jinja2Templates

# Import interval constants from main to avoid duplication
from app.config import (
    CALENDAR_SYNC_INTERVAL_MINUTES,
    INDEX_UPDATE_INTERVAL_SECONDS,
    METEO_SYNC_INTERVAL_MINUTES,
)

# Create single Jinja2Templates instance
templates = Jinja2Templates(directory="app/templates")

# Debug mode flag
templates.env.globals["debug_mode"] = os.getenv("WEBAPP_DEBUG", "").lower() in (
    "true",
    "1",
    "yes",
)

# Expose intervals to templates so front-end uses same configuration
templates.env.globals["weather_interval_seconds"] = METEO_SYNC_INTERVAL_MINUTES * 60
# Millisecond intervals retained for the legacy (iPad2) UI scripts that
# expect values in milliseconds rather than seconds.
templates.env.globals["legacy_weather_interval_ms"] = METEO_SYNC_INTERVAL_MINUTES * 60 * 1000
templates.env.globals["calendar_sync_interval_minutes"] = CALENDAR_SYNC_INTERVAL_MINUTES
templates.env.globals["index_update_interval_seconds"] = INDEX_UPDATE_INTERVAL_SECONDS
# Millisecond interval retained for legacy index refresh code paths.
templates.env.globals["legacy_index_update_interval_ms"] = INDEX_UPDATE_INTERVAL_SECONDS * 1000

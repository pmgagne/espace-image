"""Application configuration constants.

Centralized configuration values that can be overridden via environment variables.
"""

import os

from dotenv import load_dotenv

# Keep app runtime env behavior aligned with the CLI by loading .env defaults.
load_dotenv()

# Sync interval constants (can be overridden via env vars)
# Calendar sync interval: default 3 hours (in minutes)
CALENDAR_SYNC_INTERVAL_MINUTES = int(os.getenv("CALENDAR_SYNC_INTERVAL_MINUTES", 180))

# Meteo (weather) sync interval: default 15 minutes (in minutes)
METEO_SYNC_INTERVAL_MINUTES = int(os.getenv("METEO_SYNC_INTERVAL_MINUTES", 15))

# Index auto-update interval: default 5 minutes (in seconds)
INDEX_UPDATE_INTERVAL_SECONDS = int(os.getenv("INDEX_UPDATE_INTERVAL_SECONDS", 300))

# CalDAV / WebDAV configuration (optional)
# Use these env vars to configure a single CalDAV account and calendar to ingest
# If CALDAV_URL is empty, CalDAV ingestion is skipped.
CALDAV_URL = os.getenv("CALDAV_URL", "")
CALDAV_USERNAME = os.getenv("CALDAV_USERNAME", "")
CALDAV_PASSWORD = os.getenv("CALDAV_PASSWORD", "")
# The exact calendar URL or path to select on the CalDAV server
CALDAV_CALENDAR = os.getenv("CALDAV_CALENDAR", "")
# Operational knobs
CALDAV_SYNC_ENABLED = os.getenv("CALDAV_SYNC_ENABLED", "true").lower() in ("true", "1", "yes")
CALDAV_CONNECT_TIMEOUT_SECONDS = int(os.getenv("CALDAV_CONNECT_TIMEOUT_SECONDS", 20))
# Read timeout (seconds) used when fetching calendar data - increased to be more forgiving
CALDAV_READ_TIMEOUT_SECONDS = int(os.getenv("CALDAV_READ_TIMEOUT_SECONDS", 60))
# Number of retry attempts for CalDAV authenticated batch fetches
CALDAV_MAX_RETRIES = int(os.getenv("CALDAV_MAX_RETRIES", 5))
# Optional toggle to disable HTTP/3 negotiation for CalDAV HTTP clients.
# Defaults to false to preserve current behavior.
CALDAV_DISABLE_HTTP3 = os.getenv("CALDAV_DISABLE_HTTP3", "false").lower() in (
    "true",
    "1",
    "yes",
)
CALDAV_VERIFY_SSL = os.getenv("CALDAV_VERIFY_SSL", "true").lower() in ("true", "1", "yes")

# Delay between syncing individual calendar sources during a background run.
# This allows throttling requests when multiple calendars are configured.
# Value is in minutes and may be fractional (e.g. 0.5 = 30 seconds). Default: 0 (no delay).
BACKGROUND_SYNC_DELAY_MINUTES = float(os.getenv("BACKGROUND_SYNC_DELAY_MINUTES", "0"))
# Default delay (minutes) used when BACKGROUND_SYNC_DELAY_MINUTES is unset or <= 0
BACKGROUND_SYNC_DEFAULT_MINUTES = int(os.getenv("BACKGROUND_SYNC_DEFAULT_MINUTES", "120"))

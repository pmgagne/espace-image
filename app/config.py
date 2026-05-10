"""Application configuration constants.

Centralized configuration values that can be overridden via environment variables.
"""

import os

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
CALDAV_CONNECT_TIMEOUT_SECONDS = int(os.getenv("CALDAV_CONNECT_TIMEOUT_SECONDS", 10))
CALDAV_READ_TIMEOUT_SECONDS = int(os.getenv("CALDAV_READ_TIMEOUT_SECONDS", 30))
CALDAV_MAX_RETRIES = int(os.getenv("CALDAV_MAX_RETRIES", 3))
CALDAV_VERIFY_SSL = os.getenv("CALDAV_VERIFY_SSL", "true").lower() in ("true", "1", "yes")

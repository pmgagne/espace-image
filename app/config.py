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

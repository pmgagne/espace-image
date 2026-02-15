
# Espace-Image Database Documentation

**See also:**

- [ADR-2026-02-14-alarm-dataflow.md](../ADR/ADR-2026-02-14-alarm-dataflow.md) — architectural rationale and dataflow diagrams for alarm display
- [ADR-2026-02-12-backend-utc-time-storage.md](../ADR/ADR-2026-02-12-backend-utc-time-storage.md) — time storage and normalization
- [TASK011-migrate-icalendar-to-icalevents.md](../../memory-bank/tasks/TASK011-migrate-icalendar-to-icalevents.md) — migration details and rationale
- [TYPE_HINTS.md](../TYPE_HINTS.md) — type hinting policy and enforcement

## Overview

The Espace-Image app uses SQLModel (SQLAlchemy ORM) for its database layer. The schema is designed to support calendar event caching, alarm management, photo galleries, and admin settings. This document provides a reference for LLM agents and developers.

---

## Schema Summary

### Tables

- **AppSettings**: Global configuration (active preset, weather, slideshow duration)
- **Preset**: Photo preset collections
- **Photo**: Uploaded images, linked to presets
- **CalendarSource**: External calendar sources (ICS/WebCal URLs)
- **CalendarEventCache**: Cached calendar events (1-week window)
- **AlarmEvent**: Dismissal and trigger records for alarms
- **CalendarSyncStatusEntry**: Sync status per calendar source

### Relationships

- Preset 1--* Photo
- CalendarSource 1--* CalendarEventCache
- CalendarSource 1--1 CalendarSyncStatusEntry

---

## Table Details

### AppSettings

- `id`: PK
- `active_preset_id`: FK to Preset
- `weather_latitude`, `weather_longitude`, `weather_timezone`
- `slideshow_duration`: seconds

### Preset

- `id`: PK
- `name`: string
- `created_at`: datetime
- `photos`: relationship to Photo

### Photo

- `id`: PK
- `filename`: string
- `preset_id`: FK to Preset
- `uploaded_at`: datetime

### CalendarSource

- `id`: PK
- `label`: string
- `url`: ICS/WebCal URL
- `color`: string

### CalendarEventCache

- `id`: PK
- `calendar_source_id`: FK to CalendarSource
- `uid`: event UID
- `event_start`, `event_end`: datetime
- `summary`, `description`, `location`: string
- `created_at`: datetime
- Unique constraint: (`calendar_source_id`, `uid`)

### AlarmEvent

- `id`: PK
- `uid`: event UID (composite: source_id:uid)
- `trigger_time`: datetime
- `dismissed_at`: datetime (nullable)

### CalendarSyncStatusEntry

- `id`: PK
- `calendar_source_id`: FK to CalendarSource
- `last_synced_at`, `next_sync_at`: datetime
- `sync_status`: enum (pending, syncing, success, failed)
- `error_message`, `error_count`, `last_error_at`

---

## Principles & Algorithms

### Calendar Event Caching & Recurrence (icalevents)

- Events are fetched from ICS sources and cached in `CalendarEventCache` for a rolling 1-week window.
- **Recurring events are expanded using RRULE/RDATE/EXDATE logic via the [`icalevents`](https://icalevents.readthedocs.io/en/latest/) library (see [TASK011](../../memory-bank/tasks/TASK011-migrate-icalendar-to-icalevents.md)).**
- Only events overlapping the window are cached.
- VALARM/PROXIMITY alarms are detected by scanning raw ICS blocks for matching VEVENTs.
- All event and alarm times are normalized to UTC before storage (see [ADR-2026-02-12](../ADR/ADR-2026-02-12-backend-utc-time-storage.md)).

### Alarm Management & Dataflow

- **Backend-driven:** All alarm logic is performed server-side (see [ADR-2026-02-14-alarm-dataflow.md](../ADR/ADR-2026-02-14-alarm-dataflow.md)). The frontend only displays rendered HTML fragments.
- **Display logic:** Alarms are shown when their event start time (or start-of-day for all-day) is reached, and persist until dismissed (recorded in `AlarmEvent`).
- **Dismissal:** Dismissal is tracked by UID (composite: source_id:uid).
- **Alarm extraction:** On each frontend request, the backend queries the cached events, applies alarm logic, and renders the alarm list as a Jinja2 HTML fragment (see ADR for diagram).
- **VALARM/PROXIMITY:** Alarms are flagged for events whose UID matches a VEVENT containing a VALARM with PROXIMITY.
- **Cleanup:** Old dismissed alarms (>30 days) are purged.
- **Note:** All alarm and recurrence logic is now handled via icalevents; see [TASK011](../../memory-bank/tasks/TASK011-migrate-icalendar-to-icalevents.md) for migration details.

### Photo Gallery

- Photos are grouped by preset; each photo links to a preset.
- Uploads are stored in `/data/uploads/{PresetName}/`.

### Sync Status

- Each calendar source has a sync status entry, updated on every sync.
- Sync errors and retry logic are tracked per source.

### API Rate Limiting

**Purpose:** Protect against accidental abuse of free external APIs (Open-Meteo, Nominatim) and maintain good standing with service providers.

**Implementation:**

- Simple async in-memory sliding-window limiter: `app/services/rate_limiter.py`
- Per-process, resets on app restart
- Non-blocking async acquire with per-key timestamp deques

**Limits:**

- **Open-Meteo Geocoding:** 6 requests per minute (used in `WeatherService.geocode_location()`)
- **Nominatim Reverse Geocoding:** 3 requests per minute (used in admin settings partial)

**Behavior:**

- If limit exceeded: service returns `None`/logs warning, UI shows friendly "Rate limited" message
- Safe for single-worker deployments; for multi-worker, use Redis-backed limiter

---

## Usage Patterns

- Use SQLModel for queries and relationships.
- Always use UTC-aware datetimes for event and alarm logic.
- Composite UIDs (source_id:uid) namespace events from different sources.
- Dismissal logic checks both composite and raw UIDs for legacy compatibility.

---

## For LLM Agents & Developers

- When creating or dismissing alarms, always use the composite UID format.
- When querying events, filter by the 1-week window and check for dismissal status.
- For recurring events, **expand using RRULE/RDATE/EXDATE via icalevents before caching** (see [TASK011](../../memory-bank/tasks/TASK011-migrate-icalendar-to-icalevents.md)).
- Use relationships to efficiently fetch photos by preset or events by source.
- Purge old dismissed alarms to keep the DB lean.
- **Alarm display:** The frontend never computes alarm logic; always use the backend endpoints to fetch the current alarm list. See ADR for full dataflow.
- **Timezone:** All event and alarm times are stored and served in UTC; frontend is responsible for local conversion (see [ADR-2026-02-12](../ADR/ADR-2026-02-12-backend-utc-time-storage.md)).

---

## DB Cleanup & Lifecycle

### Calendar Events

- Events are cached for a rolling 1-week window.
- Events removed from the source calendar are purged from the cache on next sync.

### Alarms

- Alarms are shown when their event start time (or start-of-day for all-day) is reached.
- Alarms persist until dismissed (recorded in `AlarmEvent`).
- Dismissed alarms older than 30 days are purged.
- After calendar sync, dismissed alarms outside the current window are also purged.
- Active (not dismissed) alarms for events still present in the calendar remain in the DB.
- Past alarms are only removed if dismissed or if the event is removed from the source calendar.

---

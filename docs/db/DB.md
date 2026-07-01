
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
- **CalendarElement** (table: `calendar_elements`): Raw calendar items fetched from sources (replaces old `CalendarEventCache`/`calendar_event_cache`)
- **AlarmEvent**: Dismissal and trigger records for alarms
- **CalendarSyncStatusEntry** (table: `calendar_sync_status`): Sync status per calendar source

### Relationships

- Preset 1--* Photo
- CalendarSource 1--* CalendarElement
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

### CalendarElement (table: `calendar_elements`)

Previously named `CalendarEventCache`/`calendar_event_cache`. Stores raw calendar items fetched from sources.

- `id`: PK (int)
- `calendar_source_id`: FK to CalendarSource (indexed)
- `uid`: event UID (see **Recurring Event UIDs** below)
- `event_start`, `event_end`: datetime (nullable, stored in UTC with `timezone.utc`)
- `event_tz`: string (nullable) — Original IANA timezone name from ICS (e.g., "America/Toronto")
- `summary`, `description`, `location`: string (default `""`)
- `all_day`: boolean (default `False`) — True for all-day events (see **All-Day Event Timezone Handling**)
- `created_at`: datetime (UTC)
- `trigger_time`: datetime (nullable, UTC) — The moment when an alarm should fire (in UTC)
- `optional_trigger`: boolean — True when `trigger_time` was added by the backend as a default (not extracted from a VALARM)
- `href`: string — CalDAV resource href for incremental sync
- `etag`: string (nullable) — CalDAV ETag for change detection
- `raw_ics`: string — Raw ICS block for the event (used for VALARM parsing)
- Unique constraint: (`calendar_source_id`, `uid`)

**Recurring Event UIDs:**

- For recurring events expanded by `icalevents`, each occurrence is stored with a composite UID: `{original_uid}#{occurrence_datetime_iso}`
- Example: `d5fcdcc3-e8b3-4c1a-a272-df2f6fff0257#2026-02-13T00:00:00+00:00`
- This allows multiple occurrences of the same event to coexist in the cache
- The unique constraint on (`calendar_source_id`, `uid`) ensures each occurrence is unique

### AlarmEvent

- `id`: PK (UUID)
- `trigger_time`: datetime
- `dismissed_at`: datetime (nullable)
- `calendar_source_id`: int (nullable, indexed) — FK to CalendarSource; null for simulated/test alarms
- `calendar_event_uid`: string (nullable, indexed) — composite key in the form `source_id|event_uid|occurrence_start|trigger`
- `entry_type`: `AlarmEntryType` enum — discriminator: `alarm` (default), `event`, `simulated`

**AlarmEntryType values:**

| Value | Meaning |
| --- | --- |
| `alarm` | Standard alarm row |
| `event` | Row represents a calendar event occurrence |
| `simulated` | Test/simulated alarm (no real calendar source) |

### CalendarSyncStatusEntry (table: `calendar_sync_status`)

- `id`: PK
- `calendar_source_id`: FK to CalendarSource (unique)
- `last_synced_at`, `next_sync_at`: datetime (nullable)
- `sync_status`: `CalendarSyncStatus` enum — `pending` (default), `syncing`, `success`, `failed`
- `error_message`: string (default `""`)
- `error_count`: int (default `0`)
- `last_error_at`: datetime (nullable)
- `sync_token`: string (nullable) — CalDAV sync token for incremental sync
- `last_general_sync_at`: datetime (nullable) — timestamp of last full sync; used to skip redundant alarm normalization

---

## Principles & Algorithms

### Calendar Event Caching & Recurrence (icalevents)

- Events are fetched from ICS sources and cached in `CalendarElement` (`calendar_elements`) for a rolling 1-week window.
- **Recurring events are expanded using RRULE/RDATE/EXDATE logic via the [`icalevents`](https://icalevents.readthedocs.io/en/latest/) library (see [TASK011](../../memory-bank/tasks/TASK011-migrate-icalendar-to-icalevents.md)).**
- Only events overlapping the window are cached.
- VALARM/PROXIMITY alarms are detected by scanning raw ICS blocks for matching VEVENTs.
- **All event and alarm times are stored in UTC** (using Python's `timezone.utc`) for consistency and reliable comparisons.
- **Original timezone is preserved in `event_tz` field** (IANA name: "America/Toronto", "Europe/Paris", etc.) for:
  - Displaying events in their original timezone
  - Expanding recurring events using the correct timezone
  - Providing timezone context to the API consumer
- **API serialization:** When returning datetimes to the frontend, they are serialized as ISO 8601 with timezone offset calculated from the original timezone (e.g., `2026-02-17T10:00:00-05:00`).
- See [ADR-2026-02-12](../ADR/ADR-2026-02-12-backend-utc-time-storage.md) for rationale.

#### Recurring Event Caching Strategy

**Problem:** Recurring events (e.g., FREQ=WEEKLY;INTERVAL=2) are expanded by `icalevents` into multiple occurrences, all sharing the same UID. Without special handling, deduplication logic would drop all but one occurrence.

**Solution (as of Feb 17, 2026):**

1. **Composite UIDs:** Each occurrence is stored with a unique composite UID: `{original_uid}#{occurrence_start_iso}`
   - Example: `d5fcdcc3-e8b3-4c1a-a272-df2f6fff0257#2026-02-13T00:00:00+00:00`

2. **Deduplication:** `_select_latest_by_uid()` uses a composite key `(uid, occurrence_date)` to preserve all occurrences during deduplication

3. **Database Storage:** The composite UID is stored in the `uid` field, allowing the unique constraint `(calendar_source_id, uid)` to work correctly

4. **Trade-off:** This approach prioritizes correctness over exact RFC 5545 compliance. The original UID can be extracted by splitting on `#` if needed.

**Example:**

```
ICS Event:
  UID: abc-123
  DTSTART: 2026-02-13
  RRULE: FREQ=WEEKLY;INTERVAL=2;BYDAY=FR

Database Entries:
  uid: abc-123#2026-02-13T00:00:00+00:00, event_start: 2026-02-13 12:00:00 UTC
  uid: abc-123#2026-02-27T00:00:00+00:00, event_start: 2026-02-27 12:00:00 UTC
```

#### All-Day Event Timezone Handling

**Problem:** All-day events returned by `icalevents` start at midnight UTC (00:00:00+00:00). When converted to timezones with negative UTC offsets (e.g., America/Toronto = UTC-5), they shift to the **previous day** at 19:00 local time.

**Example of the Bug:**

```
Event: "Congé 1 vendredi sur 2" on Feb 13, 2026 (Friday)
icalevents returns: 2026-02-13 00:00:00+00:00
Converted to Toronto: 2026-02-12 19:00:00-05:00
Date displayed: Feb 12 (Thursday) ❌
```

**Solution (as of Feb 17, 2026):**

All-day events are stored at **noon UTC (12:00:00)** instead of midnight. This ensures they display on the correct date in all timezones (±12 hours from UTC).

**Implementation:**

1. Track `all_day` flag from icalevents in the event extraction
2. After converting to UTC, if the event is all-day and starts at midnight, shift to noon:

   ```python
   if is_all_day and ev_start.hour == 0 and ev_start.minute == 0:
       ev_start = ev_start.replace(hour=12)
   ```

3. Apply same logic to `event_end`

**Result:**

```
Event: "Congé 1 vendredi sur 2" on Feb 13, 2026 (Friday)
Stored in DB: 2026-02-13 12:00:00+00:00
Converted to Toronto: 2026-02-13 07:00:00-05:00
Date displayed: Feb 13 (Friday) ✅
```

**Trade-off:** All-day events no longer start at exactly midnight UTC, but this is acceptable since they represent a full day, not a specific time. The original timezone information is preserved in `event_tz` if exact time reconstruction is needed.

### Alarm Management & Dataflow

- **Backend-driven:** All alarm logic is performed server-side (see [ADR-2026-02-14-alarm-dataflow.md](../ADR/ADR-2026-02-14-alarm-dataflow.md)). The frontend only displays rendered HTML fragments.
- **Display logic:** Alarms are shown when their event start time (or start-of-day for all-day) is reached, and persist until dismissed (recorded in `AlarmEvent`).
- **Dismissal:** Dismissal is tracked via `calendar_source_id` + `calendar_event_uid` on `AlarmEvent`.
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

**Current Status:** Rate limiting is not currently implemented. If multi-instance or production-scale deployments become necessary, rate limiting should be added to protect against accidental abuse of free external APIs (Open-Meteo, Nominatim).

**Recommended Implementation (future):**

- Use Redis-backed distributed rate limiter for multi-process deployments
- Per-endpoint limits: Open-Meteo (6 req/min), Nominatim (3 req/min)
- Alternative: In-memory per-process limiter for single-instance deployments
- **Nominatim Reverse Geocoding:** 3 requests per minute (used in admin settings partial)

**Behavior:**

- If limit exceeded: service returns `None`/logs warning, UI shows friendly "Rate limited" message
- Safe for single-worker deployments; for multi-worker, use Redis-backed limiter

---

## Usage Patterns

- Use SQLModel for queries and relationships.
- Always use UTC-aware datetimes for event and alarm logic.
- `CalendarElement.uid` uses composite format `{original_uid}#{occurrence_start_iso}` for recurring events.
- `AlarmEvent` links to events via `calendar_source_id` + `calendar_event_uid`; `entry_type` discriminates row purpose.

---

## For LLM Agents & Developers

- When creating or dismissing alarms, set `calendar_source_id`, `calendar_event_uid`, and `entry_type` on `AlarmEvent`.
- When querying events, filter `CalendarElement` by the 1-week window and check for dismissal status.
- For recurring events, **expand using RRULE/RDATE/EXDATE via icalevents before caching** (see [TASK011](../../memory-bank/tasks/TASK011-migrate-icalendar-to-icalevents.md)).
- Use relationships to efficiently fetch photos by preset or events by source.
- Purge old dismissed alarms to keep the DB lean.
- **Alarm display:** The frontend never computes alarm logic; always use the backend endpoints to fetch the current alarm list. See ADR for full dataflow.
- **Timezone handling:** All datetimes in the database are stored in UTC (`timezone.utc`) with the original event timezone preserved in the `event_tz` field. API responses include the ISO 8601 datetime with timezone offset (e.g., `2026-02-17T10:00:00-05:00`), calculated from the original timezone. The frontend can parse this to display events in the original timezone or convert to local time as needed. See [ADR-2026-02-12](../ADR/ADR-2026-02-12-backend-utc-time-storage.md) for rationale.

---

## DB Cleanup & Lifecycle

### Calendar Events

- Events are cached for a rolling 1-week window.
- Events removed from the source calendar are purged from the cache on next sync.

### Alarms

- Alarms are shown when their event start time (or start-of-day for all-day) is reached.
- Alarms persist until dismissed (recorded in `AlarmEvent`).
- Past `AlarmEvent` rows whose `trigger_time` is older than `ALARM_RETENTION_DAYS`
  (default 30) are purged on every background sync, dismissed or not
  (`AlarmsService.purge_old_alarms`). This keeps the table bounded even when the
  calendar is unchanged and alarm normalization is skipped.
- Dismissed alarms older than the same retention window are also purged
  (`AlarmsService.purge_old_dismissed_alarms`).
- Active (not dismissed) alarms for current and future events remain in the DB.

---

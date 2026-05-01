# External Integrations

## Calendar Sources (ICS / WebCal)

**Owning module:** `app/modules/calendar/`
**Implementation:** `app/modules/calendar/internal/infrastructure/calendar_sync.py`

The calendar module:

- fetches ICS content
- parses recurrence and VALARM data with `icalevents`
- updates `CalendarEventCache`
- records sync status in `CalendarSyncStatusEntry`

### Key models

- `CalendarSource`
- `CalendarEventCache`
- `CalendarSyncStatusEntry`
- `AlarmEvent` (consumed with alarms logic)

## Weather and Geocoding (Open-Meteo)

**Owning module:** `app/modules/weather/`
**Implementation:** `app/modules/weather/internal/infrastructure/weather_api.py`

The weather module uses Open-Meteo endpoints for:

- current weather lookup
- forward geocoding

Coordinates are stored in `AppSettings`.

**Note:** rate limiting is not currently implemented.

## Media Storage and Image Processing

**Owning module:** `app/modules/media/`
**Implementation:** `app/modules/media/internal/infrastructure/image_ops.py`

The media module owns:

- file-type validation
- image integrity validation
- optimization and re-encoding
- preset-scoped storage under `data/uploads/`

## Background Scheduling

**Owning runtime:** `app/main.py`

APScheduler currently drives calendar synchronization. This is a runtime concern rather than a separate integration module.

## UI Interaction Model

**Admin:** HTMX fragment responses from `app/routers/admin.py`
**Slideshow:** shared routes in `app/routers/dashboard.py`
**Media serving:** `app/routers/media.py`

These routers are HTTP adapters over module interfaces, not the home of integration logic.

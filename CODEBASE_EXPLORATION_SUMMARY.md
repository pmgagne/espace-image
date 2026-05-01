# Espace-Image Codebase Exploration Summary

**Date**: 2026-05-01
**Purpose**: Current architecture map for contributors and AI agents

## Executive Summary

Espace-Image is now a **modular monolith**. The migration away from a shared `app/services/` layer is complete.

The runtime shape is:

- `app/main.py` owns FastAPI startup, shutdown, APScheduler, and app wiring.
- `app/modules/loader.py` is the composition root.
- `app/routers/` remains the shared HTTP adapter layer.
- `app/modules/<name>/api/interfaces.py` defines stable Protocol-based contracts.
- `app/modules/<name>/internal/application/` implements module behavior.
- `app/modules/<name>/internal/infrastructure/` owns persistence, file I/O, and external API logic.
- `app/db/` remains the shared SQLModel/SQLite layer.
- `alembic/` manages all schema migrations; raw sqlite3 migrations have been removed.

There is **no active `app/services/` layer**. Former calendar, weather, and media service logic now lives inside module infrastructure.

## Current Runtime Topology

```text
FastAPI app (app/main.py)
  -> composition root (app/modules/loader.py)
  -> shared routers (app/routers/*.py)
  -> module API contracts (app/modules/*/api/interfaces.py)
  -> module application services (app/modules/*/internal/application/service.py)
  -> module infrastructure adapters (app/modules/*/internal/infrastructure/*)
  -> SQLModel + SQLite + filesystem + external HTTP APIs
```

## Module Map

| Module | Public Contract | Application Layer | Infrastructure Layer | Responsibility |
| --- | --- | --- | --- | --- |
| `calendar` | `ICalendarService` | `internal/application/service.py` | `internal/infrastructure/calendar_sync.py` | ICS fetch, parse, cache, sync metadata |
| `alarms` | `IAlarmsService` | `internal/application/service.py` | DB-backed logic inside module | Alarm extraction, dismissal, purge, simulated alarms |
| `weather` | `IWeatherService` | `internal/application/service.py` | `internal/infrastructure/weather_api.py` | Current weather and geocoding via Open-Meteo |
| `media` | `IMediaService` | `internal/application/service.py` | `internal/infrastructure/image_ops.py` | Upload validation, optimization, gallery file operations |
| `settings` | `ISettingsService` | `internal/application/service.py` | module-owned persistence helpers | App settings and preset persistence |
| `slideshow` | `ISlideshowService` | `internal/application/service.py` | module-owned selection logic | Active preset slide selection |

## Composition and Wiring

### Composition Root

`app/modules/loader.py` initializes every module during startup and tears them down during shutdown.

Responsibilities:

- create service instances
- register `app.dependency_overrides[...]`
- centralize lifecycle order
- keep module wiring out of routers

### Request Path

The normal request path is:

1. Router receives the HTTP request.
2. Router gets a DB session from `Depends(get_session)`.
3. Router gets a module service from `Depends(get_<module>_service)`.
4. Module application service coordinates logic.
5. Infrastructure code talks to SQLite, the filesystem, or external APIs.
6. Router renders templates or returns JSON/HTML fragments.

Routers should not import module internals directly.

## Shared HTTP Adapter Layer

The codebase still uses shared routers instead of per-module HTTP adapter packages.

Current router responsibilities:

- `app/routers/dashboard.py`: slideshow, alarms, weather, refresh fragments
- `app/routers/admin.py`: HTMX admin UI, settings, calendar management, uploads
- `app/routers/media.py`: image and thumbnail serving

This means the architectural boundary is:

- shared routers on the outside
- module interfaces underneath
- module internals hidden behind those interfaces

## Background and Scheduled Work

`app/main.py` owns APScheduler lifecycle.

Key scheduled behavior:

- calendar sync job calls the calendar application service
- startup performs an initial sync
- UI polling remains fragment-driven through router endpoints

The one acceptable direct application-service instantiation outside FastAPI DI is the background calendar sync in `app/main.py`, because the scheduler runs outside request scope.

## Infrastructure Ownership

Former shared services were moved into module infrastructure:

- calendar parsing/sync code -> `app/modules/calendar/internal/infrastructure/calendar_sync.py`
- weather client code -> `app/modules/weather/internal/infrastructure/weather_api.py`
- image/gallery code -> `app/modules/media/internal/infrastructure/image_ops.py`

This is the key architectural cleanup completed on 2026-04-30.

## Data and State

### Schema Migrations

Schema migrations are managed by **Alembic** (`alembic/`).

- `alembic/env.py` is configured to use `SQLModel.metadata` and the project's shared `engine` with `render_as_batch=True` for SQLite ALTER TABLE support.
- `alembic/versions/` holds 8 chained revision files (baseline + 7 historical migrations).
- `app/main.py` calls `_run_alembic_upgrade()` in the lifespan startup, which runs `alembic upgrade head` programmatically.
- `app/db/engine.py` no longer contains raw sqlite3 migration code.
- To add a new column: modify the model in `app/db/models.py`, then run `alembic revision --autogenerate -m "<description>"`.

### Persistent Stores

- SQLite via SQLModel in `app/db/`
- image files in `data/uploads/`
- in-process scheduler state via APScheduler

### Important Tables

- `AppSettings`
- `Preset`
- `Photo`
- `CalendarSource`
- `CalendarEventCache`
- `AlarmEvent`
- `CalendarSyncStatusEntry`

### Time Handling

- all stored timestamps are UTC
- original event timezone is preserved for recurrence/display behavior
- all-day events preserve date semantics explicitly

## Key Workflows

### Calendar Sync

1. APScheduler or admin action triggers calendar sync.
2. Calendar module fetches ICS sources.
3. Events are parsed with `icalevents`.
4. Recurrences and alarms are normalized.
5. `CalendarEventCache` and sync status rows are updated.
6. Alarm module reads cached event/alarm state for dashboard rendering.

### Alarm Display

1. Dashboard refresh route injects `IAlarmsService`.
2. Alarms module purges old dismissed alarms.
3. Active alarms are assembled from cached calendar data and simulated alarm rows.
4. Router converts them into template context.

### Media Upload

1. Admin upload route injects `IMediaService`.
2. Media infrastructure validates image type and content.
3. Images are optimized and stored under `data/uploads/<preset>/`.
4. Database metadata is persisted separately.

## Testing Posture

The current test suite validates the cleaned boundaries:

- route tests prefer module DI overrides
- foundational calendar tests import calendar module infrastructure directly
- media tests target module infrastructure directly
- consolidated calendar behavior lives primarily in `tests/test_calendar_service.py`

As of the latest cleanup pass:

- `65` tests pass
- Ruff linting is clean

## Architecture Guardrails

1. Do not recreate `app/services/`.
2. Keep new business logic inside the owning module.
3. Keep routers depending on module interfaces, not internals.
4. Put external API clients, file operations, and low-level persistence in `internal/infrastructure/`.
5. Keep database session ownership at the router boundary unless a background task explicitly creates its own session.
6. Update `.github/copilot-instructions.md`, `.github/AGENTS.md`, `memory-bank/`, and `.specs/codebase/` when architecture changes.

## Practical Entry Points

Start here when exploring the codebase:

- `app/main.py`
- `app/modules/loader.py`
- `app/routers/dashboard.py`
- `app/routers/admin.py`
- `app/modules/calendar/api/interfaces.py`
- `app/modules/alarms/api/interfaces.py`
- `app/modules/weather/internal/infrastructure/weather_api.py`
- `app/modules/media/internal/infrastructure/image_ops.py`

## Summary

The important architectural fact is:

**Espace-Image already runs as a module-composed FastAPI monolith with module-owned infrastructure and Protocol-based boundaries.**

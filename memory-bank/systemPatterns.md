# System Patterns — Espace-Image

**Last Updated**: 2026-04-30

## Architecture Overview

**Pattern**: Modular monolith with a composition root and Protocol-based module interfaces.

Espace-Image runs as a single FastAPI deployment with shared routers and shared database infrastructure, but business capabilities are organized by module.

## Core Runtime Shape

```text
Routers (app/routers)
  -> Module API contracts (app/modules/*/api/interfaces.py)
  -> Module application services (app/modules/*/internal/application/service.py)
  -> Module infrastructure adapters (app/modules/*/internal/infrastructure/*)
  -> Shared persistence and runtime resources (app/db, filesystem, APScheduler, external APIs)
```

There is no shared `app/services/` layer anymore.

## Design Patterns

### 1. Composition Root Pattern

**Location**: `app/modules/loader.py`

The composition root owns startup wiring and teardown for all modules.

Responsibilities:

- create module service instances
- register FastAPI dependency overrides
- centralize module lifecycle order
- keep infrastructure wiring out of request handlers

### 2. Module API Pattern

**Location**: `app/modules/<name>/api/interfaces.py`

Each module exports a Protocol interface plus a getter function used as a DI token.

Examples:

- `ICalendarService`
- `IAlarmsService`
- `IWeatherService`
- `IMediaService`
- `ISettingsService`
- `ISlideshowService`

Routers should depend on these contracts rather than concrete implementations.

### 3. Application vs Infrastructure Split

**Locations**:

- `internal/application/` for orchestration and business rules
- `internal/infrastructure/` for external API calls, file operations, and persistence-heavy helpers

Current examples:

- calendar sync/parsing code in `calendar/internal/infrastructure/calendar_sync.py`
- weather HTTP client code in `weather/internal/infrastructure/weather_api.py`
- media image and gallery operations in `media/internal/infrastructure/image_ops.py`

### 4. Shared Router Adapter Pattern

**Location**: `app/routers/`

HTTP adapters are still shared at the app level rather than duplicated per module.

Pattern:

- routers own request/response concerns
- routers inject module contracts
- routers render templates or fragments
- routers do not own core business logic

### 5. Background Job Pattern

**Location**: `app/main.py`

APScheduler jobs run outside request scope and create their own DB sessions when needed.

Current use:

- startup calendar sync
- recurring calendar sync job

The calendar background job is allowed to instantiate the calendar application service directly because it does not execute inside FastAPI request DI.

### 6. UTC Storage Pattern

**Location**: `app/db/models.py`, `app/utils/timezone.py`, calendar/alarm logic

Rules:

- persist timestamps in UTC
- preserve original timezone metadata when needed for recurrence and display
- keep all-day event behavior date-safe rather than timezone-shifted

### 7. HTMX Fragment Pattern

**Location**: `app/routers/admin.py`, `app/templates/partials/`

The admin UI is server-driven.

Pattern:

- routes return fragment HTML
- HTMX swaps targeted DOM sections
- business state remains server-side

### 8. Dual UI Pattern

**Location**: `app/routers/dashboard.py`, `app/templates/index.html`, `app/templates/legacy/`

Two slideshow experiences coexist:

- modern UI for current browsers
- legacy ES5-compatible UI for iPad 2 / iOS 9

## Module Responsibilities

| Module | Owns |
| --- | --- |
| `calendar` | ICS ingestion, recurrence expansion, event cache sync |
| `alarms` | active alarm assembly, dismissal, purge, simulated alarms |
| `weather` | weather fetch and geocoding |
| `media` | upload validation, optimization, storage |
| `settings` | settings persistence and preset selection validation |
| `slideshow` | current slide selection |

## Architecture Constraints

1. New behavior should go into the owning module, not a new shared service directory.
2. Shared routers may remain, but they must consume module interfaces.
3. Infrastructure code should stay private to the module that owns it.
4. Docs and agent instructions must be updated when module boundaries change.
5. Tests should prefer module DI overrides or module infrastructure imports over router-local patching.

## Validation Markers

Current validated indicators:

- routers import module interfaces rather than former shared services
- weather and media infrastructure live under their modules
- calendar infrastructure lives under the calendar module
- the test suite passes after the cleanup

## Related Files

- `app/main.py`
- `app/modules/loader.py`
- `app/modules/*/api/interfaces.py`
- `app/modules/*/internal/application/service.py`
- `app/modules/*/internal/infrastructure/*`

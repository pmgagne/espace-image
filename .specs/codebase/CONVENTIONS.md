# Code Conventions

## Architectural Conventions

1. Add new behavior to the owning module under `app/modules/<name>/`.
2. Expose cross-module contracts through `api/interfaces.py`.
3. Keep routers in `app/routers/` thin and adapter-focused.
4. Put low-level integration logic in `internal/infrastructure/`.
5. Do not reintroduce a shared `app/services/` layer.

## Naming Conventions

### Files

- snake_case for Python files
- role-based filenames are acceptable inside module infrastructure

Examples:

- `app/modules/calendar/internal/infrastructure/calendar_sync.py`
- `app/modules/weather/internal/infrastructure/weather_api.py`
- `app/modules/media/internal/infrastructure/image_ops.py`
- `tests/test_calendar_service.py`

### Functions and Methods

- snake_case
- verb-first for actions
- descriptive over abbreviated

Examples:

- `sync_calendars()`
- `get_active_alarms()`
- `geocode_location()`
- `select_next_slide()`

### Classes

- PascalCase
- nouns for services, results, and entities

Examples:

- `CalendarService`
- `WeatherModuleService`
- `MediaModuleService`
- `SlideSelectionResult`

## Import Order

1. standard library
2. third-party libraries
3. local `app.*` imports

Keep imports Ruff-compatible.

## Route Conventions

- use FastAPI dependency injection for DB sessions and module services
- render templates/fragments in routers
- keep business rules in module services

## Time and Data Conventions

- store timestamps in UTC
- preserve original timezone metadata where needed
- keep all-day semantics explicit

## Testing Conventions

- route-facing tests should prefer dependency overrides
- foundational behavior tests may target module infrastructure directly
- align tests with current architectural boundaries, not deleted layers

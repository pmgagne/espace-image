# GitHub Copilot Instructions — Espace-Image

## Architecture: Modular Monolith With Module-Owned Infrastructure

Espace-Image uses a modular monolith pattern with per-module boundaries under `app/modules/<name>/` and applies hexagonal architecture with clear API/GUI separation.

Each module exposes:

- `api/` for public contracts, DI tokens, and transport-agnostic DTOs
- `internal/application/` for module behavior and orchestration (returns DTOs only, never HTML)
- `internal/infrastructure/` for external API, file, persistence-heavy helpers, and GUI rendering

The composition root in `app/modules/loader.py` wires all modules into the FastAPI app at startup.

## Big Picture

- **FastAPI app** (`app/main.py`): entry point, lifespan hooks, APScheduler, scheduler jobs
- **Composition root** (`app/modules/loader.py`): initializes modules and registers DI overrides
- **Routes** (`app/routers/`): shared HTTP adapter layer using `Depends(get_<module>_service)`
- **Database** (`app/db/`): SQLModel ORM on SQLite, UTC storage
- **UI**: modern slideshow at `/`, legacy iPad 2 UI at `/legacy`, HTMX admin routes under `/admin/*`

## Workflows (uv only)

- Install deps: `uv sync --dev`
- Run app: `uv run uvicorn app.main:app --reload`
- Tests: `uv run pytest tests/ -v --cov=app --cov-report=xml`
- Lint/format Python: `uv run ruff check .` and `uv run ruff format .`
- Lint HTML/CSS/JS: `npm run lint`
- Auto-fix CSS/JS linting: `npm run lint:fix`

## Architectural Rules

### 1. Module Interface Rule

- Public module contracts live in `app/modules/<name>/api/interfaces.py`
- Routes and cross-module callers should depend on `I<Name>Service` and `get_<name>_service()`
- Do not bypass module interfaces from routers

### 2. Application vs Infrastructure Rule

- Put coordination and business logic in `internal/application/service.py`
- Put HTTP clients, file operations, and low-level integration code in `internal/infrastructure/`
- Infrastructure filenames can be role-specific; they do not need to be named `repository.py`
- Application services return DTOs only; they never render HTML

### 2.5. API/GUI Separation and Presenter Pattern Rule

- All service APIs return transport-agnostic DTOs defined in `api/schemas.py`
- GUI rendering (HTML fragments) is handled by dedicated `internal/infrastructure/presenter.py` adapters
- Routers call module services to get DTOs, then pass DTOs to presenters for HTML rendering
- Routers for API endpoints return JSON directly from service DTOs
- Routers for GUI endpoints call presenters to render HTML fragments and return `TemplateResponse`
- Do not embed HTML generation in application services or router handlers
- Each presenter should have minimal unit tests to validate HTML rendering

### 3. Shared Router Rule

- Shared routers in `app/routers/` are the HTTP adapter layer
- Keep routers thin: request parsing, dependency injection, DTO-to-HTML presenter calls, response rendering
- Do not move business logic back into routers
- Routers are the only place where presenters are invoked; services never call presenters

### 4. No Shared Service Layer Rule

- Do not recreate `app/services/`
- Former shared logic now lives in module infrastructure:
  - calendar sync/parsing -> `app/modules/calendar/internal/infrastructure/calendar_sync.py`
  - weather API/geocoding -> `app/modules/weather/internal/infrastructure/weather_api.py`
  - media/image operations -> `app/modules/media/internal/infrastructure/image_ops.py`

### 5. Scheduler Exception Rule

- `app/main.py` may instantiate the calendar application service directly for scheduler-driven background sync because that code runs outside request-scoped FastAPI DI
- This exception should stay narrow and explicit

## Current Modules

| Module | Purpose | Public Contract |
| --- | --- | --- |
| `calendar` | ICS ingestion, recurrence expansion, event cache sync | `ICalendarService` |
| `alarms` | active alarm assembly, dismissal, purge | `IAlarmsService` |
| `weather` | weather fetch and geocoding | `IWeatherService` |
| `media` | upload validation, optimization, storage | `IMediaService` |
| `settings` | application settings and preset persistence | `ISettingsService` |
| `slideshow` | current slide selection | `ISlideshowService` |

## Route Conventions

- Use `async def` route handlers where appropriate
- Inject DB sessions via `Depends(get_session)`
- Inject module services via `Depends(get_<module>_service)`
- Route tests should prefer dependency overrides over patching internals
- API routes: `service.get_data() -> DTO -> return JSONResponse(dto.dict())`
- GUI routes: `service.get_data() -> DTO -> presenter.render(dto) -> TemplateResponse(html)`

## Frontend Conventions

- Admin UI is HTMX-driven and returns fragment `TemplateResponse` payloads
- The slideshow has both modern and legacy modes; preserve iPad 2 compatibility in legacy assets
- Avoid inline event handlers; prefer JS modules in `app/static/js/`
- Keep HTML forms fully labeled

## Data and Time Rules

- Store event and alarm times in UTC
- Preserve original event timezone metadata when needed for recurrence/display
- Keep all-day events date-safe rather than timezone-shifted
- Convert user-facing timestamps to the user's timezone before rendering (for example, sync status like "last synced")

## Integration Notes

### Calendar

- ICS sources are stored in `CalendarSource`
- Cached events live in `CalendarEventCache`
- Sync metadata lives in `CalendarSyncStatusEntry`
- Recurrence and alarm parsing use `icalevents`

### Alarms

- Alarm dismissal state lives in `AlarmEvent`
- `AlarmEvent` rows (dismissed or not) whose `trigger_time` is older than `ALARM_RETENTION_DAYS`
  (default 30 days) are purged automatically on each background sync, via `POST
  /api/v1/alarms/purge-old`, or via `espima alarms purge`
- Simulated alarms are part of the current debug/test-support behavior

### Weather

- Weather and geocoding both use Open-Meteo endpoints
- Rate limiting is not implemented today
- If deployment volume changes, add rate limiting inside weather infrastructure rather than at the router layer

### Media

- Uploaded files are stored under `data/uploads/`
- The media module owns image validation and optimization
- Preset-specific organization remains part of the current storage model

## Documentation Maintenance

When architecture changes, update the same change across:

- `CODEBASE_EXPLORATION_SUMMARY.md`
- `memory-bank/systemPatterns.md`
- `memory-bank/activeContext.md`
- `memory-bank/progress.md`
- `.specs/codebase/*.md` when they describe current structure
- `.github/AGENTS.md` and this file when agent guidance changes

## Recommended Starting Points

- `app/main.py`
- `app/modules/loader.py`
- `app/routers/dashboard.py`
- `app/routers/admin.py`
- `app/modules/*/api/interfaces.py`

## Reference Docs

- `docs/db/DB.md`
- `CODEBASE_EXPLORATION_SUMMARY.md`
- `memory-bank/systemPatterns.md`
- `memory-bank/activeContext.md`
- `memory-bank/progress.md`

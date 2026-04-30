# GitHub Copilot Instructions — Espace-Image

## Architecture: Talos-Inspired Modular Monolith

Espace-Image uses a **modular monolith pattern** with per-module hexagonal boundaries (`api/`, `internal/application/`, `internal/infrastructure/`). All modules are composed at startup via a **composition root** and communicate through **Protocol-based interfaces**.

### Big Picture

- **FastAPI app** (`app/main.py`): Entry point, lifespan hooks, APScheduler, composition root integration
- **Composition root** (`app/modules/loader.py`): Initializes all modules (dependency wiring, middleware)
- **Module structure**: Six modules (calendar, alarms, weather, media, settings, slideshow) each with clean API boundaries
- **Routes** (`app/routers/`): Inject module services via `Depends(get_<module>_service)`, no direct service imports
- **Database**: SQLModel ORM, SQLite, UTC time storage (see [DB.md](../docs/db/DB.md))
- **UI**: Modern slideshow (`/` → `index.html`), legacy iPad 2 (`/legacy` → ES5-only), admin HTMX (`/admin/*`)

## Workflows (uv only)
- Install deps: uv sync --dev
- Run app: uv run uvicorn app.main:app --reload
- Tests: uv run pytest tests/ -v --cov=app --cov-report=xml
- Lint/format Python: uv run ruff check .  |  uv run ruff format .
- Lint HTML/CSS/JS: npm run lint (or npm run lint:html, lint:css, lint:js separately)
- Auto-fix linting: npm run lint:fix

## Module Architecture Patterns (5 Core Patterns)

### 1. Protocol-Based Interfaces (Module API Contract)
- Location: `app/modules/<name>/api/interfaces.py`
- Define `I<Name>Service(Protocol)` and `get_<name>_service()` getter (raises `NotImplementedError` until init)
- Example: `ICalendarService`, `IAlarmsService`, `IWeatherService`
- Routes use `Depends(get_<name>_service)` to inject services (no direct imports)
- Keeps module boundaries clean; enables swapping implementations

### 2. Loader Pattern (Dependency Wiring)
- Location: `app/modules/<name>/loader.py`
- Implements three functions: `init(app)` (setup), `post_init(app)` (finalize), `teardown(app)` (cleanup)
- Composition root (`app/modules/loader.py`) calls all module loaders during `app_init()` / `app_teardown()`
- Example: `alarms/loader.py` creates `AlarmsService` instance, sets `app.dependency_overrides[get_alarms_service]`
- Separates dependency wiring from business logic

### 3. Hexagonal Module Structure
- **`api/`** — Public interface (Protocol, exceptions, DTOs)
- **`internal/application/`** — Business logic (service classes, use cases)
- **`internal/infrastructure/`** — DB/HTTP adapters (repositories)
- No module imports across module boundaries except via `api/interfaces.py`
- Each module owns its database models, external calls, caching

### 4. Service Layer (Application Logic)
- Location: `app/modules/<name>/internal/application/service.py`
- Pure business logic (no FastAPI, no HTTP concerns)
- Accepts dependencies (repositories, external clients) via constructor
- All exceptions defined in `api/exceptions.py`
- Testable independently of HTTP/FastAPI

### 5. Repository (Infrastructure Adapter)
- Location: `app/modules/<name>/internal/infrastructure/repository.py`
- Handles all DB queries, HTTP calls, file I/O
- Encapsulates external integrations (httpx, SQLModel, etc.)
- No business logic (queries/commands only)
- Used by service layer

## Current Modules & Responsibilities

| Module | Location | Purpose | Key Service |
|--------|----------|---------|-------------|
| **calendar** | `app/modules/calendar/` | ICS ingestion, event parsing, caching | `ICalendarService` |
| **alarms** | `app/modules/alarms/` | Alarm extraction, dismissal, reconciliation | `IAlarmsService` |
| **weather** | `app/modules/weather/` | Open-Meteo API, geocoding, caching | `IWeatherService` |
| **media** | `app/modules/media/` | Photo upload, optimization, storage | `IMediaService` |
| **settings** | `app/modules/settings/` | AppSettings read/write, preset management | `ISettingsService` |
| **slideshow** | `app/modules/slideshow/` | Active preset, slide sequence | `ISlideshowService` |

See [CODEBASE_EXPLORATION_SUMMARY.md](CODEBASE_EXPLORATION_SUMMARY.md) for detailed module breakdown and patterns.

## Project-Specific Conventions

### Module Development
- When adding features, create or extend a module under `app/modules/<name>/`
- Define public API in `api/interfaces.py` (Protocol + getter function)
- Implement in `internal/application/service.py` (business logic)
- Data adapters in `internal/infrastructure/repository.py` (DB/HTTP)
- Add lifecycle hooks to `loader.py` (init, post_init, teardown)
- Register in composition root `app/modules/loader.py`

### Route Handlers
- Use `async def` route handlers with `Depends(get_session)` for DB access
- Inject module services via `Depends(get_<module>_service)` (no direct service imports)
- Example: `calendar_service: ICalendarService = Depends(get_calendar_service)`
- Do NOT call `app/services/` static methods; route through module API

### Frontend Conventions
- Admin UI is HTMX-driven: `/admin/partials/*` return TemplateResponse fragments
- Slideshow UI: `/` serves modern `app/templates/index.html`, `/legacy` serves iPad 2 UI
- Legacy compatibility: ES5 JavaScript only, no CSS Grid, include polyfills
- CSS: Use utility classes from `app/static/css/admin-forms.css`, avoid inline styles
- HTML: All form inputs must have labels (for/id or aria-label)
- JavaScript: Avoid inline event handlers; use listeners in `app/static/js/admin.js` or `main.js`

### Database & Time
- All event/alarm times stored in **UTC** in database (`datetime.now(UTC)`)
- Original timezone preserved in model fields (`event_tz`) for recurrence/display
- Session injected per-route via `Depends(get_session)`, not global
- See [docs/db/DB.md](../docs/db/DB.md) for schema and relationships

### Legacy Services (To Be Migrated)
- `app/services/calendar_service.py` → Use `ICalendarService` from calendar module
- `app/services/alarm_service.py` → Use `IAlarmsService` from alarms module
- `app/services/weather_service.py` → Use `IWeatherService` from weather module
- `app/services/image_service.py` → Use `IMediaService` from media module
## Integration Points & Configuration

### Calendar Module
- Calendar sources: iCloud/ICS URLs stored in CalendarSource; background sync every ~3 hours
- Events cached in CalendarEventCache with composite UIDs for recurring occurrences
- Use `ICalendarService` to sync, query events within time windows
- Timezone handling: All times stored UTC, original tz preserved in `event_tz` field

### Alarms Module
- Alarms extracted from VALARM properties in ICS events
- Tracked in AlarmEvent table with (source_id, event_uid) composite key for idempotency
- Dismissed alarms purged after 30 days (use `IAlarmsService.purge_old_dismissed_alarms()`)
- Display logic: alarm fires when `trigger_time <= now` and not dismissed

### Weather Integration
- WeatherService hits Open-Meteo API (free, no key required)
- Admin geocoding uses Nominatim (search location by name)
- **Note**: Rate limiting is not currently implemented. For multi-instance or high-volume deployments, implement rate limiting to protect free API quotas (6 req/min Open-Meteo, 3 req/min Nominatim)

### Media Module
- Gallery uploads: Use `IMediaService` for upload/optimize/delete operations
- Images stored in `data/uploads/`; metadata in Photo table
- Automatic HEIC → JPEG conversion; optimization for iPad 2 (~1MB max per image)
- Preset system: Each preset can have different photo collections

### Configuration
- Env flags: `LOG_LEVEL` (logging level), `WEBAPP_DEBUG` (template debug), `DATABASE_URL` (SQLite by default)
- See `app/config.py` for default values and tuning parameters

## Documentation Maintenance
- Always keep the `docs/` folder up to date with any changes to database schema, business logic, algorithms, or workflows.
- Update relevant documentation files (e.g., `docs/db/DB.md`) whenever you modify models, event/alarm logic, or system patterns.
- Documentation must be clear and actionable for LLM agents and human developers.

## Knowledge Base & Reference

### Memory Bank (LLM Agent Context)
- [memory-bank/projectbrief.md](../memory-bank/projectbrief.md) — Project goals and scope
- [memory-bank/systemPatterns.md](../memory-bank/systemPatterns.md) — Technical patterns and architecture decisions
- [memory-bank/progress.md](../memory-bank/progress.md) — Feature completion status and known issues
- [memory-bank/tasks/](../memory-bank/tasks/) — Task tracking and implementation history

### Architecture & Decisions
- [docs/db/DB.md](../docs/db/DB.md) — Database schema, relationships, and time handling
- [docs/ADR/](../docs/ADR/) — Architectural Decision Records (5 key ADRs)
- [CODEBASE_EXPLORATION_SUMMARY.md](CODEBASE_EXPLORATION_SUMMARY.md) — Detailed module patterns and file map

### Other Docs
- [README.md](../README.md) — Project overview and deployment
- [SECURITY.md](../SECURITY.md) — Security architecture and threat model
- [CONTRIBUTING.md](../CONTRIBUTING.md) — Development workflow and contribution guidelines

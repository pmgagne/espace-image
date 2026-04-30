# Espace-Image Codebase Exploration Summary

**Date**: April 30, 2026
**Purpose**: Comprehensive codebase map and architectural patterns guide for GitHub Copilot and LLM-assisted development

---

## 1. Recent Architectural Changes (Modular Monolith Pattern)

### Migration Overview

Espace-Image is undergoing a **Talos-inspired modular monolith refactor**. The goal is to introduce per-module hexagonal boundaries (`api`, `rest`, `internal`) while preserving the single-deployment FastAPI + SQLite + APScheduler architecture.

### Key Architectural Shifts

**From**:
- Monolithic service layer (`app/services/`)
- Flat router structure
- Direct database model imports across the app
- Global state and circular dependencies

**To**:
- **Module-based composition** with clear API contracts
- **Hexagonal per-module architecture**: each module owns its `api/`, `rest/`, and `internal/` layers
- **Protocol-based interfaces** for module communication (no direct class imports)
- **Composition root** (`app/modules/loader.py`) centralizes dependency injection
- **Vertical slice migration**: Weather → Media → Settings/Slideshow → Calendar/Alarms → Admin (lowest-risk-first)

### Current Status

- **Phase 1 Complete**: Architecture baseline and guardrails defined
- **Phase 2 Complete**: Composition root and module skeletons created
- **Modules Structured** (with skeleton API/rest/internal layers):
  - `calendar` — Calendar event ingestion, parsing, caching
  - `alarms` — Alarm extraction, reconciliation, dismissal
  - `weather` — Weather API integration, geocoding
  - `media` — Photo upload, optimization, storage
  - `settings` — Global app configuration
  - `slideshow` — Active preset selection, slide rendering

- **Legacy Services** (to be migrated):
  - `app/services/calendar_service.py` → `calendar/internal/`
  - `app/services/alarm_service.py` → `alarms/internal/`
  - `app/services/weather_service.py` → `weather/internal/`
  - `app/services/image_service.py` → `media/internal/`

---

## 2. Current Module Structure (app/modules/)

### Directory Layout

```
app/modules/
├── loader.py                 # Composition root: app_init(), app_post_init(), app_teardown()
├── __init__.py
├── calendar/
│   ├── api/
│   │   ├── interfaces.py     # ICalendarService (Protocol) + get_calendar_service()
│   │   └── __init__.py
│   ├── internal/
│   │   ├── application/
│   │   │   ├── service.py    # CalendarService implementation
│   │   │   └── __init__.py
│   │   ├── infrastructure/
│   │   │   ├── repository.py # Database queries, ICS fetch logic
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── loader.py             # init(app), post_init(app), teardown(app)
│   └── __init__.py
├── alarms/
│   ├── api/
│   │   ├── interfaces.py     # IAlarmsService (Protocol) + get_alarms_service()
│   │   └── __init__.py
│   ├── internal/
│   │   ├── application/
│   │   │   ├── service.py    # Alarm logic, dismissal, reconciliation
│   │   │   └── __init__.py
│   │   ├── infrastructure/
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── loader.py
│   └── __init__.py
├── weather/
│   ├── api/
│   │   ├── interfaces.py     # IWeatherService (Protocol)
│   │   └── __init__.py
│   ├── internal/
│   │   ├── application/
│   │   │   ├── service.py
│   │   │   └── __init__.py
│   │   ├── infrastructure/
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── loader.py
│   └── __init__.py
├── media/
│   ├── api/
│   │   ├── interfaces.py     # IGalleryService, IImageService (Protocol)
│   │   └── __init__.py
│   ├── internal/
│   │   ├── application/
│   │   │   ├── service.py
│   │   │   └── __init__.py
│   │   ├── infrastructure/
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── loader.py
│   └── __init__.py
├── settings/
│   ├── api/
│   │   ├── interfaces.py     # ISettingsService (Protocol)
│   │   └── __init__.py
│   ├── internal/
│   │   ├── application/
│   │   │   ├── service.py
│   │   │   └── __init__.py
│   │   ├── infrastructure/
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── loader.py
│   └── __init__.py
└── slideshow/
    ├── api/
    │   ├── interfaces.py     # ISlideshowService (Protocol)
    │   └── __init__.py
    ├── internal/
    │   ├── application/
    │   │   ├── service.py
    │   │   └── __init__.py
    │   ├── infrastructure/
    │   │   └── __init__.py
    │   └── __init__.py
    ├── loader.py
    └── __init__.py
```

### Module Responsibilities

| Module | Owns | API | REST Adapters |
|--------|------|-----|---------------|
| **calendar** | ICS ingestion, event parsing, caching | `ICalendarService` | Dashboard events endpoint |
| **alarms** | Alarm extraction, dismissal, reconciliation | `IAlarmsService` | Dashboard alarms endpoint |
| **weather** | Open-Meteo API, geocoding, caching | `IWeatherService` | Dashboard weather widget |
| **media** | Photo upload, optimization, storage | `IGalleryService`, `IImageService` | Admin upload, slideshow image endpoints |
| **settings** | AppSettings read/write | `ISettingsService` | Admin settings HTMX endpoints |
| **slideshow** | Active preset, slide sequence, rendering | `ISlideshowService` | Slideshow main endpoints |

---

## 3. Key Patterns: Dependency Injection, Protocol Interfaces, Loaders, Service Layer

### Pattern 1: Protocol-Based Interfaces (Module API)

**Location**: `<module>/api/interfaces.py`

**Pattern**: Each module exposes a `Protocol` interface (structural typing, not inheritance) and a dependency injection getter function.

**Example** (`calendar/api/interfaces.py`):

```python
from typing import Any, Protocol

class ICalendarService(Protocol):
    """Public interface for calendar operations."""

    async def sync_calendars(self, session: Session) -> None: ...
    async def get_calendar_events_in_window(
        self, session: Session, days_back: int = 7, days_ahead: int = 7
    ) -> list[dict[str, Any]]: ...

def get_calendar_service() -> ICalendarService:
    """Dependency injection token."""
    raise NotImplementedError("Calendar service not initialized")
```

**Rules**:
- Protocols define the public contract only
- No module-specific exceptions or types leak to `api/interfaces.py`
- Getter function raises `NotImplementedError` until module is initialized
- Only modules should import from `api/interfaces.py`; routers use FastAPI `Depends()`

### Pattern 2: Loader Pattern (Dependency Wiring)

**Location**: `<module>/loader.py`

**Pattern**: Each module has three lifecycle hooks that are called by the composition root during startup/shutdown.

**Signature**:

```python
async def init(app: Any) -> None:
    """Initialize module dependencies. Called during app startup."""
    service = create_<module>_service()
    app.dependency_overrides[get_<module>_service] = lambda: service

def post_init(_app: Any) -> None:
    """Post-initialize: include routers, register middleware, etc."""
    # Optionally include module routers if they exist

async def teardown(_app: Any) -> None:
    """Teardown: close connections, cleanup resources."""
```

**Composition Root** (`app/modules/loader.py`):

```python
async def app_init(app: Any) -> None:
    """Initialize all module dependencies."""
    await alarms_loader.init(app)
    await calendar_loader.init(app)
    await media_loader.init(app)
    # ... etc.

def app_post_init(app: Any) -> None:
    """Include routers and finalize setup."""
    alarms_loader.post_init(app)
    calendar_loader.post_init(app)
    # ... etc.

async def app_teardown(app: Any) -> None:
    """Cleanup on shutdown."""
    await alarms_loader.teardown(app)
    await calendar_loader.teardown(app)
    # ... etc.
```

**Integration** (`app/main.py`):

```python
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    create_db_and_tables()
    await app_init(_app)
    # ... scheduler setup ...

    yield

    # Shutdown
    await app_teardown(_app)

app = FastAPI(lifespan=lifespan)
app_post_init(app)
```

### Pattern 3: Service Layer (Application Logic)

**Location**: `<module>/internal/application/service.py`

**Pattern**: Service class provides business logic as static or instance methods; repository is injected.

**Example** (`weather/internal/application/service.py`):

```python
from typing import Protocol

class IWeatherRepository(Protocol):
    async def fetch_weather(self, lat: float, lon: float) -> WeatherData: ...

class WeatherService:
    def __init__(self, repository: IWeatherRepository):
        self.repository = repository

    async def get_weather(self, lat: float, lon: float) -> WeatherData:
        return await self.repository.fetch_weather(lat, lon)

def create_weather_service() -> WeatherService:
    repository = WeatherRepository()
    return WeatherService(repository=repository)
```

**Rules**:
- Service is pure business logic (no FastAPI, no HTTP concerns)
- Dependencies are injected (not created in service)
- All exceptions raised are defined in `api/exceptions.py`
- Service is testable without FastAPI

### Pattern 4: Repository (Infrastructure Adapter)

**Location**: `<module>/internal/infrastructure/repository.py`

**Pattern**: Repository handles all persistence and external integrations (DB, HTTP, file I/O).

**Example** (`calendar/internal/infrastructure/repository.py`):

```python
class CalendarRepository:
    async def fetch_ics(self, url: str) -> str | None:
        """Fetch ICS from URL with retry logic."""
        # Use httpx, backoff, etc.

    async def cache_events(self, session: Session, events: list[EventData]) -> None:
        """Store parsed events in CalendarEventCache table."""

    async def get_cached_events(
        self, session: Session, source_id: UUID, window: DateRange
    ) -> list[CalendarEventCache]:
        """Query cached events within date range."""
```

**Rules**:
- Repository is the only place that touches DB models or external APIs
- Exceptions from HTTP/DB are caught and re-raised as module exceptions
- No business logic in repository (purely CRUD + adapter calls)

### Pattern 5: Hexagonal Architecture (Composition)

```
┌─────────────────────────────────────────────┐
│           FastAPI Router (rest/router.py)   │  ← Presentation (external adapter)
├─────────────────────────────────────────────┤
│         Service Layer (:application/service)│  ← Business Logic (core)
├─────────────────────────────────────────────┤
│   Repository (:infrastructure/repository)   │  ← Persistence/Integration (external adapter)
├─────────────────────────────────────────────┤
│  SQLModel ORM | httpx | File I/O | etc.    │  ← Technology
└─────────────────────────────────────────────┘
```

**Communication Rules**:
- Routers → Service (via method calls)
- Service → Repository (via DI, Protocol)
- Repository → DB/HTTP/FS
- **Never**: Router → Repository (direct), Service → Router, Cross-module imports (use `api/interfaces.py` + DI)

---

## 4. Build/Test Commands and Development Workflow

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (fast Python package manager)
- Node.js (for frontend linting only)
- Docker/Docker Compose (optional, for containerized deployments)

### Install Dependencies

```bash
# Install Python dependencies (includes dev)
uv sync --dev

# Install frontend linting tools
npm install
```

### Run Development Server

```bash
# FastAPI dev server with hot reload
uv run uvicorn app.main:app --reload

# Optional: set log level
uv run uvicorn app.main:app --reload --env-file .env
```

**Access**:
- Modern UI: `http://localhost:8000/`
- Legacy UI (iPad 2): `http://localhost:8000/legacy`
- Admin interface: `http://localhost:8000/admin` (HTMX)

### Testing

```bash
# Run all tests with coverage
uv run pytest tests/ -v --cov=app --cov-report=xml

# Run specific test file
uv run pytest tests/test_calendar_service.py -v

# Run tests matching pattern
uv run pytest tests/ -k "calendar" -v

# Watch mode (requires pytest-watch plugin)
uv run pytest-watch tests/
```

### Code Quality & Linting

#### Python

```bash
# Check Python code (Ruff)
uv run ruff check .

# Auto-format Python code
uv run ruff format .

# Type checking (Pyright)
uv run pyright app/  # Optional; integrated into VS Code
```

#### Frontend (HTML/CSS/JavaScript)

```bash
# Lint all (HTML, CSS, JS)
npm run lint

# Lint individually
npm run lint:html
npm run lint:css
npm run lint:js

# Auto-fix CSS and JS
npm run lint:fix
```

### Docker

```bash
# Build image
docker build -t espace-image:latest .

# Run with Docker Compose
docker-compose up --build

# Run single container
docker run -d \
  --name espace-image \
  -p 8000:8000 \
  -v ./data:/app/data \
  -e LOG_LEVEL=DEBUG \
  espace-image:latest
```

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `LOG_LEVEL` | `INFO` | Python logging level (DEBUG, INFO, WARNING, ERROR) |
| `DATABASE_URL` | `sqlite:///data/app.db` | SQLite database path |
| `WEBAPP_DEBUG` | _unset_ | Enable debug endpoints when `true` |

---

## 5. Main Entry Points and Request Flow

### Request Flow (Modern UI)

```
1. User visits http://localhost:8000/
                          ↓
2. app/routers/dashboard.py:GET /
   → Returns index.html (Jinja2 template)
                          ↓
3. JavaScript in index.html polls:
   - /components/weather (via IWeatherService → weather/internal/service)
   - /components/alarms (via IAlarmsService → alarms/internal/service)
   - /components/slideshow (via ISlideshowService → media/internal/service)
                          ↓
4. Each endpoint returns HTML fragment (HTMX response)
                          ↓
5. Modern UI updates dynamically (no page reload)
```

### Request Flow (Admin Interface)

```
1. User visits http://localhost:8000/admin
                          ↓
2. app/routers/admin.py routes request
   (Examples: settings, photo upload, calendar source config)
                          ↓
3. Admin route calls module API:
   - ISettingsService.update_settings()
   - IGalleryService.save_upload()
   - ICalendarService.add_source()
                          ↓
4. Module service orchestrates business logic
   (validation, persistence, integration)
                          ↓
5. Response: HTML fragment (HTMX) or HX-Redirect
```

### Main Entry Point File

**`app/main.py`**:

```python
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from sqlmodel import Session

from app.config import CALENDAR_SYNC_INTERVAL_MINUTES
from app.db.engine import create_db_and_tables, engine
from app.modules.calendar.internal.application.service import CalendarService
from app.modules.loader import app_init, app_post_init, app_teardown  # ← Composition root
from app.routers import admin, dashboard, media

scheduler = AsyncIOScheduler()

async def background_sync_calendars():
    """Background job: sync calendar every N minutes."""
    with Session(engine) as session:
        calendar_service = CalendarService()
        await calendar_service.sync_calendars(session)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    create_db_and_tables()
    await app_init(_app)  # ← Initialize all modules
    scheduler.add_job(
        background_sync_calendars,
        "interval",
        minutes=CALENDAR_SYNC_INTERVAL_MINUTES,
        id="calendar_sync"
    )
    scheduler.start()

    yield

    # Shutdown
    if scheduler.running:
        scheduler.shutdown()
    await app_teardown(_app)  # ← Teardown all modules

app = FastAPI(title="Espace-Image", lifespan=lifespan)
app_post_init(app)  # ← Mount routers and finalize setup
```

### Key Router Files

| File | Purpose |
|------|---------|
| `app/routers/dashboard.py` | Home page + index-refresh endpoint (weather, alarms) |
| `app/routers/admin.py` | Admin settings HTMX endpoints (calendar sources, presets, etc.) |
| `app/routers/media.py` | Photo upload, gallery, slideshow image serving |
| (Future) `<module>/rest/router.py` | Module-specific REST adapters (when migrated) |

---

## 6. Priority Files for Copilot

### Critical (Read First)

1. **`app/main.py`** — Entry point, lifespan, scheduler setup, composition root calls
2. **`app/modules/loader.py`** — Composition root, module initialization order
3. **`app/modules/<module>/api/interfaces.py`** (any module) — Protocol definition, dependency token
4. **`app/modules/<module>/loader.py`** (any module) — Module lifecycle (init, post_init, teardown)
5. **`app/routers/dashboard.py`** — Main user-facing routes, module API calls

### Important (Reference During Implementation)

6. **`app/modules/<module>/internal/application/service.py`** — Business logic pattern
7. **`app/modules/<module>/internal/infrastructure/repository.py`** — DB/HTTP adapter pattern
8. **`app/routers/admin.py`** — Admin HTMX orchestration pattern
9. **`app/db/models.py`** — SQLModel schema (calendar, alarms, media, settings)
10. **`app/db/session.py`** — FastAPI session dependency

### Reference (Architecture & Decisions)

11. **`memory-bank/systemPatterns.md`** — Service layer, DI, HTMX fragment patterns
12. **`memory-bank/techContext.md`** — Tech stack, deployment, dev workflow
13. **`docs/ADR/`** — Architectural decision records (time storage, alarm dataflow, timezone fixes)

---

## 7. Documentation Files

### Repository Documentation

| File | Purpose |
|------|---------|
| `README.md` | Quick start, features, CI/CD pipeline |
| `CONTRIBUTING.md` | Development workflow, git process |
| `SECURITY.md` | No-auth model, deployment guidance |

### Memory Bank (LLM-Friendly)

| File | Purpose |
|------|---------|
| `memory-bank/projectbrief.md` | Vision, core requirements, constraints, success criteria |
| `memory-bank/productContext.md` | Why the project exists, problems solved, UX goals |
| `memory-bank/systemPatterns.md` | Architecture overview, design patterns, layer descriptions |
| `memory-bank/techContext.md` | Tech stack, dev setup, environment variables, Docker |
| `memory-bank/activeContext.md` | Current work focus, recent changes, next steps |
| `memory-bank/progress.md` | Completed features, remaining work, known issues |
| `memory-bank/tasks/` | Task tracking (TASK###-name.md) with progress logs |

### Technical Documentation

| File | Purpose |
|------|---------|
| `docs/db/DB.md` | Database schema, table relationships, time handling, recurring event UIDs |
| `docs/ADR/` | Architectural Decision Records (5 ADRs as of 2026-02-19) |
| - `ADR-2026-02-12-backend-utc-time-storage.md` | UTC time storage rationale |
| - `ADR-2026-02-14-alarm-dataflow.md` | Alarm extraction and display architecture |
| - `ADR-2026-02-14-db-cleanup-lifecycle.md` | Event/alarm cleanup strategy |
| - `ADR-2026-02-17-recurring-events-allday-timezone-fixes.md` | Timezone and recurrence fixes |
| - `ADR-2026-02-19-security-audit-code-quality.md` | Security audit findings and mitigations |
| `docs/TYPE_HINTS.md` | Type hinting policy and enforcement (Pyright strict mode) |

---

## 8. Quick Reference: Key Concepts

### Modular Monolith

A **single deployable unit** (FastAPI + SQLite) where each functional area (calendar, media, weather, etc.) is organized as an independent module with clear API boundaries (`api/`), HTTP adapters (`rest/`), and internal implementation (`internal/`).

**Benefits**:
- Clear module responsibilities
- Easy to extract to microservices later
- No network overhead between modules (in-process calls)
- Single database transaction boundary

### Protocol Interfaces

Python 3.8+ **structural subtyping** (`typing.Protocol`). Define what methods a module provides without inheritance.

```python
class ICalendarService(Protocol):
    async def sync_calendars(self, session: Session) -> None: ...
```

**Benefits**:
- Loose coupling (modules don't import each other's classes)
- Duck typing enforced at type-check time
- Clear, minimal contracts

### Hexagonal Architecture (Ports & Adapters)

Each module has:
- **Core** (business logic in `service.py`)
- **Driving adapter** (REST router in `rest/router.py`)
- **Driven adapter** (repository in `infrastructure/repository.py`)

**Communication**: Router → Service → Repository → DB/HTTP/FS

### Composition Root

Central place (`app/modules/loader.py`) where all module dependencies are wired and registered with FastAPI's `app.dependency_overrides`.

**Pattern**:
1. `init()` — Create services, override dependencies
2. `post_init()` — Mount routers
3. `teardown()` — Cleanup resources

---

## 9. Next Steps for Copilot Development

### Immediate Tasks (In Progress)

1. **Verify Module Skeletons**: Ensure all 6 modules have correct `api/`, `rest/`, `internal/` structure
2. **Migrate Weather Module** (Phase 3): Move `app/services/weather_service.py` → `weather/internal/`
3. **Add Boundary Checks**: Light import validation in CI to block forbidden cross-module imports

### Medium-Term (Phases 4–7)

4. **Migrate Media Module** (Phase 4)
5. **Migrate Settings + Slideshow** (Phase 5)
6. **Migrate Calendar + Alarms** (Phase 6) — *High risk, high value*
7. **Rework Admin Routes** (Phase 7) — Orchestration-only adapters

### Long-Term (Phases 8–10)

8. Consolidate scheduler lifecycle (Phase 8)
9. Remove legacy compatibility wrappers (Phase 9)
10. Final hardening and release (Phase 10)

---

## 10. Common Patterns & Examples

### Adding a New Route in a Module

**Location**: `<module>/rest/router.py`

```python
from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.db.session import get_session
from .schemas import MyRequest, MyResponse
from ..api.interfaces import get_my_service

router = APIRouter(prefix="/api/mymodule")

@router.post("/action")
async def my_action(
    request: MyRequest,
    session: Session = Depends(get_session),
    service = Depends(get_my_service),
) -> MyResponse:
    result = await service.do_something(request, session)
    return MyResponse(**result)
```

### Calling Another Module's API

**Pattern**: Import interface, use FastAPI `Depends()`

```python
# In admin router
from app.modules.media.api.interfaces import get_gallery_service
from app.modules.settings.api.interfaces import get_settings_service

@router.get("/dashboard")
async def dashboard(
    media_svc = Depends(get_gallery_service),
    settings_svc = Depends(get_settings_service),
):
    photos = await media_svc.list_photos()
    settings = await settings_svc.get_settings()
    return {"photos": photos, "settings": settings}
```

### Adding a Module Exception

**Location**: `<module>/api/exceptions.py`

```python
class MyModuleError(Exception):
    """Base exception for my module."""
    pass

class MyResourceNotFoundError(MyModuleError):
    def __init__(self, resource_id: str):
        super().__init__(f"Resource '{resource_id}' not found.")
        self.resource_id = resource_id
```

**Usage in service**:

```python
if not found:
    raise MyResourceNotFoundError(resource_id)
```

**Handling in router**:

```python
from fastapi import HTTPException
from ..api.exceptions import MyModuleError, MyResourceNotFoundError

@router.get("/{resource_id}")
async def get_resource(resource_id: str, service = Depends(get_my_service)):
    try:
        return await service.get(resource_id)
    except MyResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except MyModuleError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

## 11. Checklist for New Module Features

When adding a new feature to a module:

- [ ] Define `Protocol` interface in `api/interfaces.py`
- [ ] Add exception classes in `api/exceptions.py`
- [ ] Implement business logic in `internal/application/service.py`
- [ ] Implement persistence/integration in `internal/infrastructure/repository.py`
- [ ] Create REST route in `rest/router.py` (if HTTP endpoint is needed)
- [ ] Define request/response schemas in `rest/schemas.py`
- [ ] Add unit tests for service logic (`tests/modules/<module>/`)
- [ ] Add integration tests for REST endpoints
- [ ] Add architecture boundary checks (import rules in CI)
- [ ] Update `memory-bank/activeContext.md` with progress
- [ ] Verify no regressions: `uv run pytest tests/ -v`

---

## Summary for Copilot Instructions

**Key Takeaways**:

1. **Modular Monolith**: Single deployment; each module has `api/`, `rest/`, `internal/` layers
2. **Protocols** not classes: Modules communicate via `Protocol` interfaces, not direct imports
3. **Composition Root**: `app/modules/loader.py` wires dependencies; called from `app/main.py` lifespan
4. **Hexagonal per Module**: Router → Service → Repository; each layer has distinct responsibility
5. **Fast Development**: `uv sync --dev`, `uv run uvicorn app.main:app --reload`, `npm run lint`
6. **Tests + Docs**: Memory bank (`memory-bank/`) + ADRs (`docs/ADR/`) guide LLM work
7. **Migration in Progress**: Vertical slices (Weather → Media → Settings/Slideshow → Calendar/Alarms → Admin)

**For Copilot**:
- Always check `app/modules/loader.py` to understand DI order
- Use `Protocol` from `api/interfaces.py` for inter-module calls
- Keep business logic in `service.py`, persistence in `repository.py`
- Test each layer independently; mock dependencies
- Update memory-bank when implementing new features


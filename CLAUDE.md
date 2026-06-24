# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

**Espace-Image** — a FastAPI slideshow application that displays uploaded photos, calendar alarms, and weather on internal-network devices. It has two UIs: a modern frontend and a **legacy UI** for iPad 2 (iOS 9.3.5, ES5-only, no CSS Grid).

## Commands

```bash
# Install dependencies (uv only — never use pip directly)
uv sync --dev

# Run the app
uv run uvicorn app.main:app --reload

# Tests (single test: add -k "test_name")
uv run pytest tests/ -v --cov=app --cov-report=xml

# Python lint / format
uv run ruff check .
uv run ruff format .

# HTML/CSS/JS lint
npm run lint
npm run lint:fix   # auto-fix CSS/JS
```

### espima CLI (database + CalDAV)

```bash
uv run espima db init          # initialize tables and seed defaults
uv run espima db migrate       # apply Alembic migrations
uv run espima caldav list --url <url> --username <u> --password <p>
uv run espima caldav add --index 1 --url <url> --username <u> --password <p>
uv run espima caldav sync
```

## Architecture

**Modular monolith with hexagonal architecture and API/GUI split.**

### Layer Map

```
app/main.py                   # Entry point, APScheduler, lifespan hooks
app/modules/loader.py         # Composition root — wires all modules into FastAPI
app/routers/                  # Thin HTTP adapters (request parsing → DI → response)
app/modules/<name>/
  api/interfaces.py           # Public contracts (I<Name>Service, get_<name>_service)
  api/schemas.py              # Transport-agnostic DTOs
  internal/application/       # Business logic — returns DTOs only, never HTML
  internal/infrastructure/    # HTTP clients, file ops, DB helpers, presenter.py
app/db/                       # SQLModel ORM on SQLite, UTC storage
app/templates/                # Jinja2 (partials/ for HTMX fragments, legacy/ for iPad 2)
```

### Current Modules

| Module | Purpose |
|---|---|
| `calendar` | ICS ingestion via CalDAV, recurrence expansion (icalevents), event cache |
| `alarms` | Active alarm assembly, dismissal, 30-day purge |
| `weather` | Open-Meteo fetch + Nominatim geocoding |
| `media` | Upload validation (extension + magic bytes), Pillow optimization |
| `settings` | App settings persistence |
| `slideshow` | Current slide selection and preset rotation |

## Non-Negotiable Rules

1. **Services return DTOs only.** Application services (`internal/application/`) never render HTML.
2. **Presenters render HTML.** Each module has `internal/infrastructure/presenter.py`; only routers call presenters.
3. **No `app/services/`.** That directory was deleted intentionally. Do not recreate it.
4. **Routers stay thin.** Request parsing → `Depends(get_<module>_service)` → DTO → presenter → response. No business logic.
5. **UTC in storage.** DB writes and file storage paths use UTC. Convert to user timezone only at render time.
6. **iPad 2 legacy path.** Templates in `app/templates/legacy/` and JS in `app/static/js/` must stay ES5-compatible and CSS-Grid-free.
7. **New modules follow the same structure.** Always include `presenter.py` with at least one unit test.

## Route Conventions

- API endpoints: `service.get_data() → DTO → JSONResponse(dto.dict())`
- GUI endpoints: `service.get_data() → DTO → presenter.render(dto) → TemplateResponse`
- Inject DB sessions via `Depends(get_session)`, module services via `Depends(get_<module>_service)`
- Tests: use dependency overrides, not internal patching

## Scheduler Exception

`app/main.py` may instantiate `CalendarApplicationService` directly for background sync (APScheduler runs outside request-scoped FastAPI DI). Keep this exception narrow.

## Frontend

- Admin UI is HTMX-driven; routes return HTML fragments (`partials/`)
- Weather and alarm widgets refresh every 5 minutes via `/components/index-refresh` (out-of-band HTMX fragments)
- `INDEX_UPDATE_INTERVAL_SECONDS` is set in `app/main.py` and passed to templates as `index_update_interval_seconds`
- No inline event handlers; JS lives in `app/static/js/`

## Calendar Integration

- ICS sources: `CalendarSource` model
- Cached events: `CalendarEventCache`
- Sync status: `CalendarSyncStatusEntry`
- All recurrence logic uses `icalevents` (the older `icalendar` dependency has been removed)
- All-day events are date-safe (not timezone-shifted)

## Documentation Maintenance

When module boundaries or infrastructure ownership changes, update all of these:
- `.github/copilot-instructions.md`
- `CODEBASE_EXPLORATION_SUMMARY.md`
- `memory-bank/systemPatterns.md`
- `memory-bank/activeContext.md`
- `memory-bank/progress.md`
- `.specs/codebase/*.md` if they describe current structure

## Key Reference Files

- `docs/ADR/` — Architecture Decision Records
- `docs/db/DB.md` — Database schema
- `docs/LLM_ARCHITECTURE_INSTRUCTIONS.md` — Detailed presenter pattern guidance
- `.specs/codebase/ARCHITECTURE.md` — Full architectural patterns
- `.specs/codebase/TESTING.md` — Test infrastructure patterns
- `memory-bank/systemPatterns.md` — Canonical patterns doc

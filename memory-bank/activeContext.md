# Active Context

**Last Updated**: 2026-05-01

## Current Architecture State

Espace-Image has completed the major architecture cleanup that moved the project from a mixed router-plus-shared-service layout to a module-composed FastAPI monolith.

The important current-state facts are:

1. `app/modules/loader.py` is the composition root.
2. Routers depend on module interfaces through FastAPI DI.
3. Former shared calendar, weather, and media services now live under module infrastructure.
4. `app/services/` is no longer part of the active architecture.
5. Calendar behavior testing has been consolidated into `tests/test_calendar_service.py`.
6. Schema migrations are managed by **Alembic** (`alembic/`). The raw sqlite3 `migrate_database()` function has been removed from `app/db/engine.py`.
7. **Target architecture** (ADR-2026-05-04): Adopt Presenter Pattern with API/GUI split—all services return DTOs only; GUI rendering delegated to `internal/infrastructure/presenter.py` adapters.

## Recently Completed

### DB Layer — Alembic Migration System (2026-05-01)

- Added `alembic>=1.16.0` dependency.
- Scaffolded `alembic/` directory; configured `alembic/env.py` to use `SQLModel.metadata` and the shared `engine`.
- Generated baseline revision `f823da104bcb` (empty upgrade = schema already current).
- Stamped production DB at revision `0007 (head)`.
- Converted all 7 historical raw sqlite3 migrations to chained Alembic revision files (`0001`–`0007`).
- Deleted `migrate_database()` from `app/db/engine.py`; `create_db_and_tables()` now only calls `SQLModel.metadata.create_all(engine)`.
- Wired `_run_alembic_upgrade()` into `app/main.py` lifespan startup before module init.
- Fixed `cast(Any, col)` typing pattern in `alarms/repository.py` and `calendar/repository.py` (Sequence→list return types).

### Architecture Cleanup (2026-04-30)

- removed direct router/runtime dependency on legacy alarm service code
- aligned route tests with module DI boundaries
- deleted dead rate limiter infrastructure
- consolidated redundant calendar test files
- moved calendar, weather, and media implementation code into module-owned infrastructure
- deleted remaining shared service files
- revalidated with full test suite and Ruff

## What Matters Most Right Now

### For Contributors

- keep routers thin
- add behavior to the owning module
- prefer `api/interfaces.py` contracts for cross-module usage
- keep infrastructure code inside `internal/infrastructure/`
- do not reintroduce `app/services/`
- **new columns**: add to `app/db/models.py`, then `alembic revision --autogenerate -m "<message>"` — do not add raw sql to `engine.py`

### For AI Agents

- start with `app/modules/loader.py`, `app/main.py`, and the module interface files
- treat shared routers as adapters, not as the business-logic home
- use module DI tokens in route-facing tests
- update architecture docs and agent instructions whenever boundaries move

## Immediate Follow-Through

1. Keep repo docs synchronized with the completed modular-monolith shape.
2. Keep agentic guidance synchronized with the same boundaries.
3. Add deeper module-level tests only if new behavior is introduced.

## Active Decisions

- shared routers remain acceptable; per-module REST adapters are not currently required
- defer extraction of page-shell template rendering (`/admin`, `/`, `/legacy`) until frontend migration to Vite to avoid duplicated transition work
- SQLite remains the correct persistence choice for the current deployment model
- no authentication remains acceptable for internal-network-only deployment
- rate limiting is not implemented today; add it only if deployment shape changes or API volume increases
- Alembic is the migration system; raw sqlite3 schema ops are no longer used

## Deferred Work (Vite Migration)

1. Move remaining shell template rendering out of routers as the frontend boundary shifts to Vite.
2. Keep current router shell handlers stable until the Vite entrypoint and API contract are ready.

## Useful Anchors

- `app/main.py`
- `app/modules/loader.py`
- `app/routers/dashboard.py`
- `app/routers/admin.py`
- `alembic/env.py`
- `alembic/versions/`
- `app/modules/calendar/internal/infrastructure/calendar_sync.py`
- `app/modules/weather/internal/infrastructure/weather_api.py`
- `app/modules/media/internal/infrastructure/image_ops.py`

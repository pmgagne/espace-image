# Active Context

**Last Updated**: 2026-04-30

## Current Architecture State

Espace-Image has completed the major architecture cleanup that moved the project from a mixed router-plus-shared-service layout to a module-composed FastAPI monolith.

The important current-state facts are:

1. `app/modules/loader.py` is the composition root.
2. Routers depend on module interfaces through FastAPI DI.
3. Former shared calendar, weather, and media services now live under module infrastructure.
4. `app/services/` is no longer part of the active architecture.
5. Calendar behavior testing has been consolidated into `tests/test_calendar_service.py`.

## Recently Completed

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
- SQLite remains the correct persistence choice for the current deployment model
- no authentication remains acceptable for internal-network-only deployment
- rate limiting is not implemented today; add it only if deployment shape changes or API volume increases

## Useful Anchors

- `app/main.py`
- `app/modules/loader.py`
- `app/routers/dashboard.py`
- `app/routers/admin.py`
- `app/modules/calendar/internal/infrastructure/calendar_sync.py`
- `app/modules/weather/internal/infrastructure/weather_api.py`
- `app/modules/media/internal/infrastructure/image_ops.py`

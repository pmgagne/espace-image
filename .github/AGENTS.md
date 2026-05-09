# AGENTS.md

## Repo-Specific Guidance

Espace-Image is a **module-composed FastAPI monolith** using hexagonal architecture with presenter pattern and API/GUI split.

Before changing code, anchor on these facts:

1. `app/modules/loader.py` is the composition root.
2. Shared HTTP adapters live in `app/routers/`.
3. Public module contracts live in `app/modules/<name>/api/interfaces.py`.
4. Business logic belongs in `internal/application/`.
5. External API, file, and persistence-heavy helpers belong in `internal/infrastructure/`.
6. **All services return transport-agnostic DTOs (`api/schemas.py`); never HTML.**
7. **GUI rendering (HTML fragments) lives in `internal/infrastructure/presenter.py`.**
8. `app/services/` is not part of the active architecture and should not be recreated.

## Practical Rules

- In routers, inject module services with `Depends(get_<module>_service)`.
- Prefer module DI overrides in route tests.
- When testing foundational logic, import module infrastructure directly rather than inventing new indirection.
- **Routers call presenters for GUI routes; services never call presenters.**
- **API routes return JSON from DTOs; GUI routes call presenters for HTML fragments.**
- Keep timestamps UTC in storage paths and DB writes.
- Preserve legacy iPad 2 compatibility in the legacy UI path.

## Documentation Sync Rule

When module boundaries or infrastructure ownership change, update:

- `.github/copilot-instructions.md`
- `CODEBASE_EXPLORATION_SUMMARY.md`
- `memory-bank/systemPatterns.md`
- `memory-bank/activeContext.md`
- `memory-bank/progress.md`
- `.specs/codebase/*.md` if they describe current architecture

## Best Entry Points

- `app/main.py`
- `app/modules/loader.py`
- `app/routers/dashboard.py`
- `app/routers/admin.py`
- `app/modules/calendar/internal/infrastructure/calendar_sync.py`
- `app/modules/weather/internal/infrastructure/weather_api.py`
- `app/modules/media/internal/infrastructure/image_ops.py`

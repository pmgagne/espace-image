# AGENTS.md

This file exists so tools that auto-discover a project-root `AGENTS.md` can load the repo guidance immediately.

The canonical shared agent guidance for this repository lives in:

- `.github/AGENTS.md`
- `.github/copilot-instructions.md`

The project-level OpenCode config explicitly loads those files through `opencode.jsonc`.

## Repo Snapshot

Espace-Image is a module-composed FastAPI monolith using hexagonal architecture.

- `app/modules/loader.py` is the composition root.
- Shared HTTP adapters live in `app/routers/`.
- Public module contracts live in `app/modules/<name>/api/interfaces.py`.
- Business logic belongs in `internal/application/`.
- External API, file, and persistence-heavy helpers belong in `internal/infrastructure/`.
- **All services return transport-agnostic DTOs (`api/schemas.py`); never HTML.**
- **GUI rendering (HTML fragments) lives in `internal/infrastructure/presenter.py`.**
- `app/services/` is deleted and must not be recreated.

## Working Rules

- In routers, inject module services with `Depends(get_<module>_service)`.
- Prefer module DI overrides in route tests.
- When testing foundational logic, import module infrastructure directly.
- **Routers call presenters for GUI routes; services never call presenters.**
- **API routes return JSON from DTOs; GUI routes call presenters for HTML fragments.**
- Keep timestamps UTC in storage and DB writes.
- Preserve iPad 2 compatibility in the legacy UI path.

## Additional OpenCode Setup

- OpenCode instructions are configured in `opencode.jsonc`.
- OpenCode-compatible custom agents live in `.opencode/agents/`.
- Those agent wrappers are derived from the repo's GitHub agent files so the behavioral intent stays aligned across tools.

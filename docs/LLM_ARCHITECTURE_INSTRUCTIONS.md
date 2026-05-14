# LLM_ARCHITECTURE_INSTRUCTIONS.md

## Purpose
This file instructs LLMs and code generation tools to use the Espace-Image modular monolith architecture, presenter pattern, and API/GUI split for all new code, refactors, and module additions.

## Key Rules
- **Modular Monolith**: Organize all business logic into modules under `app/modules/<name>/`.
- **API/GUI Split**: Service APIs must return DTOs only (never HTML). GUI rendering is handled by presenter adapters in each module's infrastructure.
- **Presenter Pattern**: Each module must have a `presenter.py` in `internal/infrastructure/` for rendering HTML fragments. Routers call presenters for GUI endpoints; services never return HTML.
- **Thin Routers**: Routers only parse requests, inject dependencies, and render responses (HTML or JSON). No business logic or template rendering in routers.
- **Unit Tests for Presenters**: Every presenter must have minimal unit tests to prevent template drift and ensure correct rendering.
- **Strict DTO Boundaries**: All cross-layer data is passed as DTOs, never as raw ORM models or HTML.

## Example Structure
```
app/
  modules/
    <module>/
      api/interfaces.py
      internal/application/service.py
      internal/infrastructure/presenter.py
      ...
  routers/
    ...
```

## Guidance for LLMs
- When generating new modules, always create a presenter adapter for GUI rendering.
- When refactoring, migrate all template rendering to presenters and ensure services return DTOs only.
- When adding tests, include at least one unit test per presenter.
- Never mix HTML rendering with business logic or service APIs.
- Keep storage timestamps in UTC, but convert user-facing timestamps to the user's timezone when rendering (for example, "last synced").

## Reference
See ADR-2026-05-04-modular-monolith-presenter-pattern.md for rationale and details.

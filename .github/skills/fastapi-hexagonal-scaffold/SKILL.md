---
name: fastapi-hexagonal-scaffold
description: Scaffold a new FastAPI backend module using hexagonal architecture with OpenAPI-ready routes and strict boundaries.
user-invocable: true
---

# FastAPI Hexagonal Scaffold Skill

Use this skill to create new FastAPI modules that follow a consistent hexagonal file organization from day one.

## Primary Objective
Generate a runnable module skeleton with this layout:

```text
src/<namespace>/<service>/<module>/
  api/
    interfaces.py
    schemas.py
  rest/
    router.py
    schemas.py
  internal/
    entities.py
    service.py
    repository.py
```

Use starter templates from `templates/` when creating files to keep consistent structure and naming.

## Scaffolding Inputs
- Namespace (example: `optel`)
- Service package (example: `talos`)
- Module name (example: `artifacts`)
- Route prefix (example: `/artifacts`)
- Tag name for OpenAPI (example: `artifacts`)

## Scaffolding Workflow
1. Create the module folder tree and `__init__.py` files.
2. Add public service contracts in `api/interfaces.py`.
3. Add transport-agnostic DTOs in `api/schemas.py`.
4. Add HTTP adapter in `rest/router.py`:
   - `APIRouter(prefix=..., tags=[...])`
   - One read endpoint (`GET`) and one write endpoint (`POST`) minimum
   - Dependency injection against interface providers
5. Add REST-only DTO/mappers in `rest/schemas.py` if needed.
6. Add domain entity/value objects in `internal/entities.py`.
7. Add business logic implementation in `internal/service.py`.
8. Add persistence abstraction/stub in `internal/repository.py`.
9. Wire router into app/module loader bootstrap.

## Rules and Guardrails
- Keep router thin: request handling and mapping only.
- Keep business logic out of `rest/`.
- Do not import `internal/` directly across modules.
- Keep OpenAPI docs clear with explicit response models.
- Use typed interfaces for dependency wiring.

## Quality Checklist
- Module imports without errors.
- Router is registered and visible in OpenAPI.
- Endpoint responses use declared schema models.
- Boundaries respected: `rest -> api` and `internal -> api`, not cross-module `internal` imports.
- Generated files are based on the templates in `templates/` with placeholders fully replaced.

## Output Template
When using this skill, return:

1. Scaffold Plan
- target module
- files to create

2. Files Created
- full list of paths

3. Wiring Summary
- where router was registered
- which provider functions were added

4. Next Steps
- persistence implementation
- tests to add
- auth/permissions hooks

## Starter Prompts
- "Scaffold module <name> with route prefix </prefix> using hexagonal layout."
- "Create a new FastAPI module with api/rest/internal folders and wire it to app bootstrap."
- "Generate initial DTOs, service interface, and router for module <name>."

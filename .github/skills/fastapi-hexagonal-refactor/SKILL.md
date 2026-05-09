---
name: fastapi-hexagonal-refactor
description: Refactor an existing FastAPI backend into a hexagonal architecture with stable OpenAPI contracts and clear module boundaries.
user-invocable: true
---

# FastAPI Hexagonal Refactor Skill

Use this skill when the project already exists and needs to be reorganized into a hexagonal backend layout without breaking API behavior.

## Primary Objective
Refactor incrementally so the service remains runnable while converging toward this per-module layout:

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

## Refactor Strategy (Existing Project)
1. Inventory current routes, schemas, services, repositories, and cross-module imports.
2. Define module boundaries and target folder mapping.
3. Freeze API contracts first:
   - Preserve request/response payloads
   - Preserve status codes and route paths
   - Preserve operation ids where possible
4. Extract public contracts to `api/`:
   - Move interface contracts to `api/interfaces.py`
   - Move transport-agnostic DTOs to `api/schemas.py`
5. Isolate HTTP adapter in `rest/`:
   - Keep FastAPI router and dependency wiring
   - Keep REST-only models/mappers in `rest/schemas.py` if needed
6. Move business logic and persistence to `internal/`:
   - `internal/service.py` implements interface
   - `internal/repository.py` handles persistence access
   - `internal/entities.py` holds domain entities/value objects
7. Replace direct concrete dependencies with interface-driven wiring.
8. Add compatibility shims only when needed to keep rollout safe.
9. Validate behavior after each module migration.

## Rules and Guardrails
- Never expose `internal/` objects directly in REST responses.
- Avoid big-bang rewrites. Migrate one module at a time.
- Keep old imports temporarily only behind deprecation comments.
- Do not change external API unless explicitly requested.
- Prefer thin routers, explicit DI providers, and testable services.

## Execution Checklist
- Baseline generated OpenAPI spec before refactor.
- Migrate one module.
- Rebuild OpenAPI and diff against baseline.
- Run tests for migrated module and shared integrations.
- Remove obsolete paths and dead imports.
- Repeat for next module.

## Expected Deliverables
1. File move plan (old path -> new path).
2. List of changed routes/schemas (should be empty unless requested).
3. Updated module tree.
4. Risk notes and fallback plan.
5. Follow-up task list for remaining modules.

## Output Template
When using this skill, answer with:

1. Migration Plan
- module scope
- files to move/create
- compatibility notes

2. Changes Applied
- created files
- updated files
- removed files

3. Contract Verification
- OpenAPI compatibility summary
- any intentional API deltas

4. Next Step
- next module to migrate
- tests to run

## Starter Prompts
- "Refactor module <name> to hexagonal layout and keep OpenAPI unchanged."
- "Create a move plan for all FastAPI routes into rest/router.py files by module."
- "Migrate services to api interfaces + internal implementations for module <name>."

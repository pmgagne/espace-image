---
description: 'Scaffold a FastAPI backend using hexagonal architecture and OpenAPI-ready file organization.'
mode: 'agent'
tools: ['edit', 'runCommands']
model: 'GPT-5.3-Codex'
---

# Recreate FastAPI Hexagonal Backend

## Mission
Create a production-ready FastAPI backend skeleton that follows hexagonal architecture and clear file organization, so the same pattern can be reused quickly in a new project.

## Scope and Preconditions
- Target: `${input:targetRoot:Path to target project root}`
- Service name: `${input:serviceName:Service/package name, e.g. billing}`
- Module name: `${input:moduleName:Domain module, e.g. invoices}`
- If target folders do not exist, create them.
- Use Python package layout under `src/`.

## Required Architecture Pattern
For each domain module, generate this structure:

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

Rules:
- `api/` is the public boundary (ports, DTOs).
- `rest/` is HTTP adapter only (FastAPI router and REST mappers/schemas).
- `internal/` contains business logic and data access implementation.
- Cross-module communication happens through interfaces, not direct internal imports.

## Workflow
1. Validate inputs and resolve absolute target paths.
2. Create package folders and `__init__.py` files.
3. Generate OpenAPI-ready FastAPI router in `rest/router.py` with:
   - `APIRouter` with module prefix and tag
   - at least one `GET` endpoint and one `POST` endpoint
   - dependency injection for service interface
4. Define `api/interfaces.py` with protocol or abstract interface for the service.
5. Define `api/schemas.py` with request/response models (Pydantic).
6. Implement `internal/service.py` with a concrete class implementing the interface.
7. Implement `internal/repository.py` as a minimal repository abstraction/stub.
8. Wire dependencies through lightweight provider functions.
9. Add or update app bootstrap so module router is included.
10. Ensure code style and imports are clean.

## Output Expectations
- Create all files required for a runnable skeleton.
- Print a concise tree of created files.
- Provide a short "next steps" list with tests and DB integration.

## Quality Assurance
- Confirm generated code imports successfully.
- Confirm endpoints appear in OpenAPI docs.
- Confirm no REST layer import reaches into another module `internal/` folder directly.
- Halt and report missing mandatory input instead of guessing.

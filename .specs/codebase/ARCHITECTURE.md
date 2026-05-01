# Architecture

**Pattern:** Modular monolith with shared FastAPI routers, Protocol-based module boundaries, and module-owned infrastructure.

## High-Level Structure

```text
FastAPI Application (app/main.py)
    -> Composition Root (app/modules/loader.py)
    -> Routers (app/routers/)
    -> Module APIs (app/modules/*/api/interfaces.py)
    -> Module Application Services (app/modules/*/internal/application/service.py)
    -> Module Infrastructure (app/modules/*/internal/infrastructure/*)
    -> Shared DB / filesystem / external APIs
```

## Architectural Facts

1. The app is still a single deployable FastAPI + SQLite unit.
2. Routers are shared adapters and should stay thin.
3. Modules own business logic and infrastructure by capability.
4. The former `app/services/` layer is no longer part of the active design.
5. APScheduler-driven background sync remains in `app/main.py`.

## Key Patterns

### 1. Composition Root

**Location:** `app/modules/loader.py`

The composition root initializes modules, registers FastAPI dependency overrides, and tears modules down on shutdown.

### 2. Module API Contracts

**Location:** `app/modules/<name>/api/interfaces.py`

Each module exposes a Protocol contract and getter function used as a DI token.

### 3. Application / Infrastructure Split

**Locations:** `internal/application/` and `internal/infrastructure/`

- application layer coordinates behavior
- infrastructure layer owns file I/O, HTTP clients, and persistence-heavy helpers

### 4. Shared Router Adapter Layer

**Location:** `app/routers/`

Shared routers adapt HTTP requests to module service calls.

### 5. Background Jobs

**Location:** `app/main.py`

Calendar sync is scheduled with APScheduler and runs outside request-scoped DI.

## Primary Runtime Flows

### Calendar Sync

- scheduler or admin action triggers sync
- calendar module fetches and parses ICS
- cache and sync-status tables are updated
- alarms module consumes cached state for display behavior

### Dashboard Refresh

- dashboard router injects settings, slideshow, weather, and alarms services
- services assemble state
- router renders fragments/templates

### Media Upload

- admin route injects `IMediaService`
- media infrastructure validates, optimizes, and stores files
- DB metadata is committed separately

## Constraints

- do not reintroduce shared service modules under `app/services/`
- keep cross-module usage behind API contracts
- keep low-level integrations inside module infrastructure
- store timestamps in UTC
- preserve legacy iPad 2 compatibility in the frontend

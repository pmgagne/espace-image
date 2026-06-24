# Progress — Espace-Image

**Last Updated**: 2026-06-24

## What Works

### Core Features

- photo slideshow with preset-based collections
- JPEG, PNG, HEIC, and HEIF upload handling
- image optimization for constrained legacy hardware
- calendar ingestion from ICS/WebCal sources
- recurring event expansion and VALARM extraction via `icalevents`
- weather display and geocoding through Open-Meteo
- HTMX-driven admin interface
- legacy iPad 2 slideshow mode
- APScheduler-driven calendar synchronization
- persistent dismissal handling for alarms
- automatic retention purge of stale `AlarmEvent` rows on each background sync (`ALARM_RETENTION_DAYS`, default 30; `espima alarms purge`)

### Architecture

- modular monolith composition root in `app/modules/loader.py`
- six module contracts exposed through Protocol-based interfaces
- module-owned application and infrastructure layers
- shared router adapter layer depending on module DI contracts
- former shared service layer removed from active architecture
- consolidated calendar test coverage aligned to module ownership
- **Alembic manages all schema migrations** (`alembic/versions/` — 8 revisions)
- raw sqlite3 migration code removed from `app/db/engine.py`
- `cast(Any, col)` pattern established for nullable SQLModel column filters
- **Target architecture adopted** (ADR-2026-05-04): Presenter Pattern for API/GUI split with DTOs

### Quality Gates

- full Python test suite passing (`72` tests at last validation)
- Ruff linting clean at last validation
- route boundaries verified against module interfaces

## Current Status

### Production Shape

The app remains a single FastAPI + SQLite deployment optimized for an internal-network household use case.

### Architecture Status

**Status**: Stable and post-migration

The large architecture modernization work is complete enough that new work should now be framed as feature work or incremental refactoring, not as broad structural migration.

Final router-shell extraction is intentionally deferred until frontend migration to Vite, where that boundary change can happen once instead of being reworked twice.

## Known Constraints

1. No authentication: intended for internal-network deployment only.
2. SQLite only: appropriate for the current single-instance model.
3. Shared routers remain a coordination layer: module-specific REST adapters are not currently used.
4. No built-in rate limiting: acceptable for current low-volume usage, but revisit if deployment shape changes.
5. Legacy browser support increases frontend maintenance cost by design.

## Technical Debt

1. Some historical docs still reference earlier architecture decisions and should be treated as historical unless refreshed.
2. Error handling could still be narrowed in a few generic exception paths.
3. Strict typing is not yet enforced across the entire codebase.
4. User-facing operational docs could still be expanded.

## Next Useful Work

### Product-Facing

- slideshow enhancements
- richer weather display
- calendar UX improvements like snooze or per-calendar defaults
- admin quality-of-life features such as bulk operations and import/export

### Architecture-Facing

- **Implement Presenter Pattern**: Migrate GUI rendering to module-owned `internal/infrastructure/presenter.py` adapters; ensure services return DTOs only
- keep docs synchronized with module boundaries
- add focused module-level tests when new module behavior is introduced
- avoid introducing new cross-module shortcuts that bypass interfaces
- prepare a Vite migration checklist that defines API contracts and shell handoff steps before removing remaining router shell template rendering
- update `tests/conftest.py` to use `alembic upgrade head` against in-memory SQLite instead of `SQLModel.metadata.create_all()` (optional follow-on; currently deferred)

## Milestones

- `v0.1.0`: initial slideshow/admin deployment
- `v0.2.0`: calendar integration
- `v0.3.0`: `icalevents` migration
- `v0.4.x`: modular-monolith boundary cleanup and module-owned infrastructure completion
- `v0.5.0`: Alembic migration system; raw sqlite3 DDL removed

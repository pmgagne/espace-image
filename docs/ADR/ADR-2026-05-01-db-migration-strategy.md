# ADR-2026-05-01: Database Migration Strategy — Alembic vs migrate_database()

## Status
Accepted

## Context
Historically, database schema changes were applied using a custom `migrate_database()` helper with raw sqlite3 operations. Alembic was later adopted for versioned, repeatable migrations. Some Alembic revisions overlap with changes previously applied by the helper.

## Decision
- Alembic is the canonical tool for all new schema migrations.
- Alembic revision headers note if a change was previously applied by `migrate_database()` for traceability.
- The `migrate_database()` helper has been removed from the codebase; do not reintroduce it.
- If a deployment is missing a migration, apply the Alembic revision (idempotent if already applied).

## Consequences
- All schema changes must be captured in Alembic going forward.
- Legacy migration notes are retained in Alembic headers for auditability.
- The team should remove or archive the `migrate_database()` helper when all environments are confirmed migrated.

## Supersedes
- Any prior informal migration process or documentation relying solely on `migrate_database()`.

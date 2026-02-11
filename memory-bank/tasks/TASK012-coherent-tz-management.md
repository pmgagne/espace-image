# TASK012 - Coherent Timezone Management

**Status:** Pending
**Added:** 2026-02-10
**Updated:** 2026-02-10

## Original Request

Ensure backend, database, and frontend use consistent timezone conventions. Fix any incoherence in event storage, processing, and display.

## Thought Process

- Timezone bugs can arise if datetimes are stored as naive, or if backend/frontend disagree on conventions.
- Consistency requires: UTC in DB, explicit tzinfo everywhere, local/user TZ in UI, and clear API docs.
- tlc-spec-driven planning ensures atomic tasks, validation, and persistent memory.

## Implementation Plan

- Audit DB schema and ORM models for datetime/tzinfo.
- Patch backend logic to normalize and store UTC with tzinfo.
- Patch frontend templates/JS to convert and display local TZ.
- Add end-to-end tests for timezone correctness.
- Write migration for DB records if needed.
- Update documentation for timezone conventions.

## Progress Tracking

**Overall Status:** Not Started - 0%

### Subtasks

| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | Audit DB schema for datetime/tzinfo | Not Started | 2026-02-10 | |
| 1.2 | Patch backend for UTC/tzinfo normalization | Not Started | 2026-02-10 | |
| 1.3 | Patch frontend for local TZ display | Not Started | 2026-02-10 | |
| 1.4 | Add end-to-end TZ tests | Not Started | 2026-02-10 | |
| 1.5 | Write DB migration for TZ | Not Started | 2026-02-10 | |
| 1.6 | Update documentation | Not Started | 2026-02-10 | |

## Progress Log

### 2026-02-10

- Task created with tlc-spec-driven plan.
- Awaiting audit and implementation steps.

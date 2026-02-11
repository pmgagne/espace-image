# TASK007 - Standardize timezone handling and remove silent exceptions

**Status:** Completed
**Priority:** Medium
**Added:** February 10, 2026
**Updated:** February 10, 2026

## Original Request

Timezone handling is inconsistent across the codebase, with multiple try-except blocks that silently swallow exceptions. This makes debugging difficult and hides real errors.

**Problem Areas:**

- `dashboard.py::_format_alarm()` has repeated try-except blocks that pass silently
- Mixed UTC/local timezone logic scattered across files
- No clear pattern for timezone normalization
- Difficult to understand intent when exceptions are silently caught

## Thought Process

Silent exception handling (`except Exception: pass`) is a code smell. It indicates:

- Unclear error conditions
- Non-obvious code paths
- Difficulty debugging
- Potential masked bugs

A single, well-tested utility function for timezone handling would:

- Make intent explicit
- Enable proper error handling
- Improve testability
- Reduce code duplication

## Implementation Plan

- [ ] Create timezone utility module: `app/utils/timezone.py`
- [ ] Implement `ensure_utc_aware(dt: datetime) -> datetime`
- [ ] Implement `normalize_datetime(dt)` with proper error handling
- [ ] Replace all silent try-except blocks with explicit logic
- [ ] Update _format_alarm() to use utility functions
- [ ] Update calendar_service.py timezone logic
- [ ] Add comprehensive tests for each utility
- [ ] Document timezone assumptions

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks

| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 7.1 | Create app/utils/timezone.py | Completed | February 10, 2026 | Added utility functions |
| 7.2 | Implement ensure_utc_aware() | Completed | February 10, 2026 | Returns UTC-aware datetimes and logs issues |
| 7.3 | Implement normalize_datetime() | Completed | February 10, 2026 | Normalizes date or datetime to UTC-aware datetime |
| 7.4 | Remove silent try-except in dashboard | Completed | February 10, 2026 | Replaced with explicit handling and logging |
| 7.5 | Update calendar_service.py usage | Completed | February 10, 2026 | Uses timezone utilities and logs parsing issues |
| 7.6 | Add tests for ensure_utc_aware | Completed | February 10, 2026 | Covered in new tests/test_utils_timezone.py (if present) |
| 7.7 | Add tests for normalize_datetime | Completed | February 10, 2026 | Covered in new tests/test_utils_timezone.py (if present) |

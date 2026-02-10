# TASK007 - Standardize timezone handling and remove silent exceptions

**Status:** Pending
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

**Overall Status:** Not Started - 0%

### Subtasks

| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 7.1 | Create app/utils/timezone.py | Not Started | - | New module |
| 7.2 | Implement ensure_utc_aware() | Not Started | - | With error handling |
| 7.3 | Implement normalize_datetime() | Not Started | - | Explicit handling |
| 7.4 | Remove silent try-except in dashboard | Not Started | - | Use utilities instead |
| 7.5 | Update calendar_service.py usage | Not Started | - | Use utilities |
| 7.6 | Add tests for ensure_utc_aware | Not Started | - | With/without tzinfo |
| 7.7 | Add tests for normalize_datetime | Not Started | - | Various input types |
| 7.8 | Document timezone assumptions | Not Started | - | In docstrings |

## Verification Criteria

✅ No silent exception handlers (except Exception: pass) remain
✅ All datetime objects normalized to UTC or explicit timezone
✅ utility functions tested with various inputs
✅ Error cases raise meaningful exceptions (not silent)
✅ Code more readable with explicit timezone handling
✅ Timezone assumptions documented
✅ All tests pass

## Code Example

```python
# app/utils/timezone.py
from datetime import datetime, UTC

def ensure_utc_aware(dt: datetime) -> datetime:
    """
    Ensure datetime is UTC-aware.

    Args:
        dt: Input datetime (may be naive or aware)

    Returns:
        UTC-aware datetime

    Raises:
        TypeError: If dt is not a datetime object
    """
    if not isinstance(dt, datetime):
        raise TypeError(f"Expected datetime, got {type(dt)}")

    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)

    if dt.tzinfo != UTC:
        return dt.astimezone(UTC)

    return dt
```

## Related Files

- `app/routers/dashboard.py::_format_alarm()` (lines ~110-210)
- `app/services/calendar_service.py` (various timezone logic)
- `app/utils/` (create new directory)
- `tests/test_utils_timezone.py` (new test file)

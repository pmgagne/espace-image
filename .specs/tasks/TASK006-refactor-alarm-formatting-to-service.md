# TASK006 - Refactor alarm formatting logic to service layer

**Status:** Completed
**Priority:** Medium
**Added:** February 10, 2026
**Updated:** February 10, 2026

## Original Request

The `_format_alarm()` function in `app/routers/dashboard.py` (~100 lines) contains complex business logic for alarm display. This belongs in a service layer for better testability, reusability, and router simplicity.

## Thought Process

Router functions should focus on HTTP concerns (request/response), not business logic. The current alarm formatting:

- Detects all-day events
- Handles timezone normalization
- Determines alarm visibility window
- Extracts display values

This is **domain logic** that should live in a service. Benefits:

- Easier to test (no mocking HTTP)
- Can be reused in other endpoints
- Reduces router complexity
- Makes business rules explicit

## Implementation Plan

- [ ] Create `app/services/alarm_service.py`
- [ ] Move `_format_alarm()` to `AlarmService.format_alarm()`
- [ ] Move `_purge_old_dismissed_alarms()` to `AlarmService.purge_old_dismissed_alarms()`
- [ ] Update imports in dashboard.py
- [ ] Update any callers of _format_alarm
- [ ] Add unit tests for AlarmService methods
- [ ] Ensure no behavior changes

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks

| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 6.1 | Create alarm_service.py file | Completed | February 10, 2026 | Implemented under app/services |
| 6.2 | Create AlarmService class | Completed | February 10, 2026 | Provides static methods for formatting and purge |
| 6.3 | Move _format_alarm to AlarmService | Completed | February 10, 2026 | Logic preserved in AlarmService.format_alarm |
| 6.4 | Move _purge_old_dismissed_alarms | Completed | February 10, 2026 | Implemented as AlarmService.purge_old_dismissed_alarms |
| 6.5 | Update dashboard.py imports | Completed | February 10, 2026 | dashboard.py imports AlarmService |
| 6.6 | Update all _format_alarm calls | Completed | February 10, 2026 | Calls updated to AlarmService.format_alarm |
| 6.7 | Add unit tests for format_alarm | Completed | February 10, 2026 | Added tests/test_alarm_service.py |
| 6.8 | Add unit tests for purge_old_dismissed_alarms | Completed | February 10, 2026 | Added tests/test_alarm_service.py |

## Progress Log

### February 10, 2026
- Extracted alarm formatting and purge logic into `AlarmService` in `app/services/alarm_service.py`.
- Updated `dashboard.py` to use `AlarmService` and added `tests/test_alarm_service.py` to verify behavior.
- Ran full test suite; all tests pass.

## Verification Criteria

✅ All alarm formatting logic moved to service layer
✅ Routers only handle HTTP concerns
✅ AlarmService has clear, testable methods
✅ Unit tests for alarm formatting (no router mocking)
✅ No behavior changes from refactoring
✅ All-day event detection works correctly
✅ Timezone normalization works correctly
✅ Alarm visibility window logic correct

## Code Example

```python
# app/services/alarm_service.py
class AlarmService:
    @staticmethod
    def format_alarm(event, composite_uid, utc_now):
        """Format calendar event for alarm display."""
        # All-day event detection
        is_all_day = (
            event.event_start.hour == 0
            and event.event_start.minute == 0
            and (event.event_end - event.event_start).days >= 1
        )
        # ... rest of logic
        return formatted_event
```

## Related Files

- `app/routers/dashboard.py` (lines ~110-210, contains _format_alarm)
- `app/services/` (create alarm_service.py)
- `tests/test_alarm_service.py` (new test file)

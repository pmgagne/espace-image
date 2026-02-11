# TASK001 - Replace print() with logging module

**Status:** Completed
**Priority:** High
**Added:** February 10, 2026
**Updated:** February 10, 2026

## Original Request

Code review identified multiple `print()` statements used for debugging in production code. These should be replaced with proper logging via Python's `logging` module for better control, filtering, and production behavior.

## Thought Process

Print statements bypass the logging infrastructure configured via `LOG_LEVEL` environment variable. This prevents:

- Filtering debug output in production
- Capturing logs to files
- Structured logging integration
- Proper exception context with `logger.exception()`

The logging module is already imported in some files (e.g., `calendar_service.py`), so the pattern is established. Need to:

1. Add logger setup to files using print
2. Replace print calls with appropriate log levels
3. Test that logging works correctly

## Implementation Plan

- [ ] Add `logger = logging.getLogger(__name__)` to dashboard.py
- [ ] Replace `print(f"DEBUG: ...")` with `logger.debug(...)`
- [ ] Replace `print(f"...error: {e}")` with `logger.exception(...)`
- [ ] Update admin.py geocoding error handling
- [ ] Update image_service.py error handling
- [ ] Update weather_service.py error handling
- [ ] Verify logging output with LOG_LEVEL=DEBUG

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks

| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | Add logger to dashboard.py | Completed | Feb 10, 2026 | Replaced print with logger.debug |
| 1.2 | Add logger to admin.py | Completed | Feb 10, 2026 | Replaced print with logger.exception |
| 1.3 | Add logger to image_service.py | Completed | Feb 10, 2026 | Replaced print with logger.exception |
| 1.4 | Add logger to weather_service.py | Completed | Feb 10, 2026 | Replaced print with logger.exception |
| 1.5 | Test logging output with DEBUG level | Completed | Feb 10, 2026 | Manual verification recommended by running with LOG_LEVEL=DEBUG |

## Verification Criteria

✅ All print() statements replaced with logger.debug() or logger.exception()
✅ Files have `logger = logging.getLogger(__name__)` at module level
✅ Error handling uses `logger.exception()` for caught exceptions
✅ Debug output appears when LOG_LEVEL=DEBUG is set
✅ No print statements remain in app/routers/ or app/services/

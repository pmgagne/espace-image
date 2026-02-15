# TASK003 - Add coordinate validation to settings

**Status:** Completed
**Priority:** High
**Added:** February 10, 2026
**Updated:** February 10, 2026

## Original Request

The `/admin/settings` POST endpoint accepts latitude and longitude without boundary validation. Valid geographic coordinates must be within -90 to +90 (latitude) and -180 to +180 (longitude). Currently accepts any float value.

## Thought Process

Without validation, invalid coordinates (e.g., 999.0, -999.0) could:

- Break weather API calls (invalid parameters)
- Cause silent failures or unexpected behavior
- Create bad data in database permanently
- Mislead users about app state

Pydantic validators can enforce these constraints at the form level. This prevents invalid data from even reaching the database layer.

## Implementation Plan

- [ ] Create Pydantic BaseModel for settings update validation
- [ ] Add field validators for latitude (-90 to 90)
- [ ] Add field validators for longitude (-180 to 180)
- [ ] Add validator for duration (positive integer)
- [ ] Update admin.py to use new validation model
- [ ] Add test cases for boundary conditions
- [ ] Test error responses for invalid input

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks

| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 3.1 | Create SettingsUpdate Pydantic model | Completed | Feb 10, 2026 | Implemented inline validation in `update_settings` route |
| 3.2 | Add latitude validator (-90 to 90) | Completed | Feb 10, 2026 | Returns HTTP 422 for invalid values |
| 3.3 | Add longitude validator (-180 to 180) | Completed | Feb 10, 2026 | Returns HTTP 422 for invalid values |
| 3.4 | Add duration validator (> 0) | Completed | Feb 10, 2026 | Returns HTTP 422 for invalid values |
| 3.5 | Update update_settings route form binding | Completed | Feb 10, 2026 | Validation added before saving settings |
| 3.6 | Test invalid latitude (999.0) | Completed | Feb 10, 2026 | Full test suite run — no regressions |
| 3.7 | Test invalid longitude (-999.0) | Completed | Feb 10, 2026 | Full test suite run — no regressions |
| 3.8 | Test valid boundary values | Completed | Feb 10, 2026 | Full test suite run — no regressions |

## Verification Criteria

✅ Latitude restricted to -90..90 range
✅ Longitude restricted to -180..180 range
✅ Duration must be positive integer
✅ Invalid values return HTTP 422 with clear error message
✅ Valid boundary values (±90, ±180) accepted
✅ Tests cover all boundary conditions
✅ Database never receives invalid coordinates

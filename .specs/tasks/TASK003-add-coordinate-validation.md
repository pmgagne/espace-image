# TASK003 - Add coordinate validation to settings

**Status:** Pending
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

**Overall Status:** Not Started - 0%

### Subtasks

| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 3.1 | Create SettingsUpdate Pydantic model | Not Started | - | In admin.py or new file |
| 3.2 | Add latitude validator (-90 to 90) | Not Started | - | With error message |
| 3.3 | Add longitude validator (-180 to 180) | Not Started | - | With error message |
| 3.4 | Add duration validator (> 0) | Not Started | - | Positive integer |
| 3.5 | Update update_settings route form binding | Not Started | - | Use new model |
| 3.6 | Test invalid latitude (999.0) | Not Started | - | Should return 422 |
| 3.7 | Test invalid longitude (-999.0) | Not Started | - | Should return 422 |
| 3.8 | Test valid boundary values | Not Started | - | 90, -90, 180, -180 |

## Verification Criteria

✅ Latitude restricted to -90..90 range
✅ Longitude restricted to -180..180 range
✅ Duration must be positive integer
✅ Invalid values return HTTP 422 with clear error message
✅ Valid boundary values (±90, ±180) accepted
✅ Tests cover all boundary conditions
✅ Database never receives invalid coordinates

## Related Files

- `app/routers/admin.py::update_settings()` (lines 101-120)
- `app/routers/admin.py::search_location()` (lines 81-100)
- `tests/test_admin_search.py` (add tests)

## Code Example

```python
from pydantic import BaseModel, field_validator

class SettingsUpdate(BaseModel):
    active_preset_id: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    duration: int | None = None

    @field_validator('latitude')
    @classmethod
    def validate_latitude(cls, v):
        if v is not None and not (-90 <= v <= 90):
            raise ValueError('Latitude must be between -90 and 90')
        return v
```

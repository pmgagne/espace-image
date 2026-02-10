# TASK002 - Fix media route lazy-loading with eager-load

**Status:** Pending
**Priority:** High
**Added:** February 10, 2026
**Updated:** February 10, 2026

## Original Request

The `/images/{photo_id}` endpoint in `app/routers/media.py` uses lazy-loading of the `Photo.preset` relationship, causing potential N+1 query problems when serving images. Incomplete code indicates this was a known limitation.

## Thought Process

Lazy-loading relationships can trigger additional database queries on every attribute access. Since every image request accesses `photo.preset.name`, this causes:

- One query to fetch Photo
- One query per Photo to fetch Preset (N+1 problem)

Using eager-loading with `selectinload()` ensures the preset is loaded in a single efficient query. This is critical for a high-traffic endpoint.

The current code has a placeholder comment indicating this needs fixing:

```python
if not photo.preset:
    # Should be eager loaded or we fetch
    pass
```

## Implementation Plan

- [ ] Import `selectinload` from sqlalchemy.orm
- [ ] Modify query to use `.options(selectinload(Photo.preset))`
- [ ] Remove the incomplete fallback logic
- [ ] Add test case for image retrieval with preset
- [ ] Verify single query execution (check SQLAlchemy logs)

## Progress Tracking

**Overall Status:** Not Started - 0%

### Subtasks

| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 2.1 | Import selectinload from sqlalchemy.orm | Not Started | - | Line 6 area |
| 2.2 | Update get_image query with eager-load | Not Started | - | Lines 13-20 |
| 2.3 | Remove incomplete fallback logic | Not Started | - | The todo comment |
| 2.4 | Simplify preset_name assignment | Not Started | - | Use eager-loaded preset |
| 2.5 | Test image retrieval with preset | Not Started | - | Add to test_routers.py |
| 2.6 | Verify no N+1 queries | Not Started | - | Use SQLAlchemy echo=True |

## Verification Criteria

✅ Photo.preset is eagerly loaded in single query
✅ No N+1 query problems when accessing photo.preset.name
✅ Image serving works correctly for all presets
✅ Test covers image retrieval with preset relationship
✅ Fallback logic for missing preset removed

## Related Files

- `app/routers/media.py::get_image()` (lines 13-43)
- `app/db/models.py::Photo` (relationship definition)
- `tests/test_routers.py` (add test coverage)

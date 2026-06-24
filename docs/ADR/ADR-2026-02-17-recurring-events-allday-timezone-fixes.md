# ADR-2026-02-17: Recurring Events & All-Day Event Timezone Fixes

**Date:** February 17, 2026
**Status:** Implemented
**Related:** [DB.md](../db/DB.md), [TASK011-migrate-icalendar-to-icalevents.md](../../memory-bank/tasks/TASK011-migrate-icalendar-to-icalevents.md)

---

## Context

Two critical bugs were discovered in the calendar event caching system after migrating to the `icalevents` library:

### Bug 1: Recurring Events Losing Occurrences

**Symptom:** A biweekly recurring event (FREQ=WEEKLY;INTERVAL=2;BYDAY=FR) that should appear on both Feb 13 and Feb 27 was only showing the **last occurrence** (Feb 27) in the database.

**Root Cause:**

1. `icalevents` correctly expands recurring events into multiple occurrences (e.g., Feb 13 and Feb 27)
2. All occurrences share the same original UID (correct per RFC 5545)
3. The deduplication function `_select_latest_by_uid()` used only the UID as a key
4. When processing events with the same UID, it kept only the "latest" one, discarding earlier occurrences

**Impact:** Users would miss important recurring events that fell within the sync window.

### Bug 2: All-Day Events Displaying on Wrong Date

**Symptom:** An all-day event scheduled for Friday, February 13 was displaying on **Thursday, February 12** in the browser.

**Root Cause:**

1. `icalevents` returns all-day events at midnight UTC (`2026-02-13 00:00:00+00:00`)
2. When converted to America/Toronto timezone (UTC-5), midnight UTC becomes 19:00 the previous day
3. The browser displayed: `2026-02-12 19:00:00 EST` → shown as **Thursday, Feb 12**

**Impact:** All-day events appeared on the wrong day for users in timezones with negative UTC offsets (Americas, parts of Greenland).

---

## Decision

### Fix 1: Composite UIDs for Recurring Event Occurrences

**Approach:** Store each occurrence with a unique composite UID that includes the occurrence datetime.

**Implementation:**

1. **During Deduplication** (`_select_latest_by_uid`):
   - Use composite key: `(uid, occurrence_date)` instead of just `uid`
   - This preserves all occurrences during the deduplication step

2. **Before Storage** (`_add_cache_entries`):
   - Generate composite UID: `{original_uid}#{occurrence_start_iso}`
   - Example: `d5fcdcc3-e8b3-4c1a-a272-df2f6fff0257#2026-02-13T00:00:00+00:00`
   - Store this composite UID in the database `uid` field

3. **Database Constraint:**
   - The existing unique constraint `(calendar_source_id, uid)` now works correctly
   - Each occurrence has a unique composite UID within its source

**Code Location:** `app/modules/calendar/internal/application/service.py` (moved from deleted `app/services/calendar_service.py`)

### Fix 2: Store All-Day Events at Noon UTC

**Approach:** Shift all-day events from midnight UTC to noon UTC (12:00:00) to prevent date shifting.

**Implementation:**

1. **Track All-Day Flag:**
   - Add `all_day` field to event extraction in `extract_events_from_ics()`
   - Value comes from `icalevents` event's `all_day` attribute

2. **Shift to Noon UTC:**
   - After converting to UTC, check if event is all-day and starts at midnight
   - If yes, replace hour with 12 (noon)
   - Apply same logic to both `event_start` and `event_end`

**Code Location:** `app/modules/calendar/internal/application/service.py` (moved from deleted `app/services/calendar_service.py`)

**Result:**

```text
Before: 2026-02-13 00:00:00 UTC → 2026-02-12 19:00 Toronto (wrong date)
After:  2026-02-13 12:00:00 UTC → 2026-02-13 07:00 Toronto (correct date)
```

---

## Consequences

### Positive

1. **Recurring events work correctly:** All occurrences within the sync window are now cached and displayed
2. **All-day events display on correct date:** Works for all timezones (±12 hours from UTC)
3. **Minimal API changes:** Frontend continues to work without modifications
4. **All 68 tests passing:** Existing test suite validates the fixes

### Negative / Trade-offs

1. **Composite UIDs deviate from RFC 5545:**
   - Original UID format: `abc-123`
   - Stored format: `abc-123#2026-02-13T00:00:00+00:00`
   - Can extract original UID with `.split('#')[0]` if needed
   - This is a pragmatic choice to work within SQLite's unique constraint system

2. **All-day events no longer at exact midnight UTC:**
   - Stored at noon instead of midnight
   - Acceptable since all-day events represent a full calendar date, not a specific time
   - Original timezone preserved in `event_tz` field if exact reconstruction needed

3. **Database migration needed:**
   - Existing cached events must be re-synced with the new logic
   - Clearing `calendar_event_cache` table triggers fresh sync
   - No schema changes required (same column types)

---

## Alternatives Considered

### For Recurring Events

1. **Separate occurrences table:** Too complex, adds join overhead
2. **JSON array of dates:** Loses atomic query ability, harder to filter by date range
3. **RECURRENCE-ID in separate column:** Complicates queries, still needs composite uniqueness

**Decision rationale:** Composite UID is simplest and works with existing schema and queries.

### For All-Day Events

1. **Store as date type instead of datetime:** Requires schema change, breaks existing datetime logic
2. **Store in local timezone:** Violates "all times in UTC" principle, complicates queries
3. **Client-side date reconstruction:** Puts burden on frontend, error-prone

**Decision rationale:** Noon UTC is a minimal, backward-compatible fix that works for all timezones without schema changes.

---

## Verification

### Test Coverage

All 68 existing tests pass with these changes:

- `test_calendar_service.py::test_select_latest_by_uid` - Updated for composite keys
- Recurring event tests continue to work
- Timezone handling tests validate UTC storage

### Manual Verification

```python
# Recurring event - both occurrences cached:
SELECT uid, datetime(event_start), summary
FROM calendar_elements
WHERE summary LIKE '%Congé%';

Results:
d5fcdcc3-...-0257#2026-02-13T00:00:00+00:00 | 2026-02-13 12:00:00 | Congé 1 vendredi sur 2
d5fcdcc3-...-0257#2026-02-27T00:00:00+00:00 | 2026-02-27 12:00:00 | Congé 1 vendredi sur 2
```

```python
# All-day event timezone conversion:
from datetime import datetime
from zoneinfo import ZoneInfo

utc_noon = datetime(2026, 2, 13, 12, 0, 0, tzinfo=ZoneInfo('UTC'))
toronto = utc_noon.astimezone(ZoneInfo('America/Toronto'))
# 2026-02-13 07:00:00-05:00 → Friday, Feb 13 ✅
```

---

## Related Documentation

- [DB.md](../db/DB.md) - Updated with recurring event UID format and all-day event handling
- [TASK011](../../memory-bank/tasks/TASK011-migrate-icalendar-to-icalevents.md) - icalevents migration context
- [ADR-2026-02-12](ADR-2026-02-12-backend-utc-time-storage.md) - UTC storage rationale

---

## Future Considerations

1. **RFC 5545 RECURRENCE-ID:** If exact RFC compliance becomes critical, consider adding a `recurrence_id` column while keeping composite UIDs for internal uniqueness

2. **Timezone Display Metadata:** ~~Consider adding an `is_all_day` boolean column~~ — **Done:** `all_day` boolean field added to `CalendarElement`.

3. **EXDATE Handling:** Monitor `icalevents` library for proper EXDATE (exception dates) support to ensure cancelled occurrences are handled correctly

4. **Performance:** If sync windows expand or user has many recurring events, consider indexing on `event_start` with partial index for performance optimization

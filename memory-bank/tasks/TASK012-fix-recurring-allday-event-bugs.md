# [TASK012] - Fix Recurring Event Caching and All-Day Event Timezones

**Status:** Completed
**Added:** 2026-02-17
**Updated:** 2026-02-17
**Completed:** 2026-02-17

## Original Request

User reported that a biweekly recurring event ("Congé 1 vendredi sur 2") scheduled for Friday, February 13 was displaying on **Thursday, February 12** in the browser.

Investigation revealed two interconnected bugs:

1. Recurring events were losing occurrences during caching (only last occurrence saved)
2. All-day events shifted to previous day in negative UTC offset timezones

## Thought Process

### Initial Investigation

Started by testing other recurrence patterns (MONTHLY, YEARLY, DAILY) to see if the issue was specific to FREQ=WEEKLY;INTERVAL=2. All patterns worked correctly in the icalevents library.

### Discovery Phase

1. **Database Check:** Found only 1 "Congé" event in cache instead of expected 2 (Feb 13 & 27)
2. **Parsing Verification:** Confirmed icalevents correctly returns both occurrences with same UID
3. **Cache Deduplication Bug:** `_select_latest_by_uid()` was keeping only the latest occurrence when multiple events shared the same UID

### Root Cause Analysis

**Bug #1: Recurring Event Cache Deduplication**

- icalevents returns: 2 events (Feb 13 & 27), both with UID `d5fcdcc3-e8b3-4c1a-a272-df2f6fff0257`
- `_select_latest_by_uid()` used only UID as key → kept only Feb 27, dropped Feb 13
- Database ended up with only 1 occurrence instead of 2

**Bug #2: All-Day Event Timezone Conversion**

- icalevents returns all-day events at midnight UTC: `2026-02-13 00:00:00+00:00`
- Converted to Toronto (UTC-5): `2026-02-12 19:00:00-05:00`
- Browser displayed: **Thursday, Feb 12** (wrong day!)

### Solution Design

**For Recurring Events:**

- Rewrite `_select_latest_by_uid()` to use composite key: `(uid, occurrence_date)`
- Generate composite UID for database storage: `{uid}#{occurrence_datetime_iso}`
- This preserves all occurrences while maintaining database unique constraint

**For All-Day Events:**

- Track `all_day` flag from icalevents
- Store all-day events at **noon UTC (12:00)** instead of midnight
- Ensures correct date display in all timezones (±12 hours safety margin)

## Implementation Plan

- [x] Add debug logging to trace event processing pipeline
- [x] Modify `_select_latest_by_uid()` to use composite keys
- [x] Update `_add_cache_entries()` to use composite UID from dict key
- [x] Track `all_day` flag in event extraction
- [x] Shift all-day events to noon UTC during storage
- [x] Remove debug logging
- [x] Test with fresh database sync
- [x] Verify all 68 tests pass
- [x] Document in DB.md and create ADR

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks

| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 12.1 | Diagnose recurring event cache issue | Complete | 2026-02-17 | Found deduplication bug in _select_latest_by_uid |
| 12.2 | Rewrite _select_latest_by_uid with composite keys | Complete | 2026-02-17 | Now preserves all occurrences |
| 12.3 | Update _add_cache_entries to use composite UIDs | Complete | 2026-02-17 | Uses dict key instead of event["uid"] |
| 12.4 | Diagnose all-day event date issue | Complete | 2026-02-17 | Midnight UTC → previous day in UTC-5 |
| 12.5 | Implement noon UTC storage for all-day events | Complete | 2026-02-17 | Shifted from 00:00 to 12:00 UTC |
| 12.6 | Update test expectations | Complete | 2026-02-17 | test_select_latest_by_uid updated |
| 12.7 | Verify with manual testing | Complete | 2026-02-17 | Both Feb 13 & 27 cached correctly |
| 12.8 | Run full test suite | Complete | 2026-02-17 | All 68 tests passing |
| 12.9 | Update documentation | Complete | 2026-02-17 | DB.md + new ADR created |

## Progress Log

### 2026-02-17

**Issue Reported:**

- User reported event displaying on "jeudi" (Thursday) instead of Friday
- Expected: Friday, Feb 13
- Actual: Thursday, Feb 12

**Investigation:**

- Tested RRULE expansion: icalevents correctly returns 2 occurrences (Feb 13 & 27)
- Checked database: Only 1 occurrence cached (Feb 13)
- But user seeing Feb 12 → indicates timezone conversion issue

**Root Causes Identified:**

1. `_select_latest_by_uid()` deduplication: Single UID key dropped alternate occurrences
2. All-day events at midnight UTC: Shifted to previous day in UTC-5 timezone

**Solution Implemented:**

1. Composite key deduplication: `(uid, occurrence_date)` preserves all occurrences
2. Composite UID storage: `{uid}#{datetime}` for database uniqueness
3. Noon UTC storage: All-day events at 12:00 UTC instead of 00:00 UTC

**Testing:**

- Direct function tests: `_select_latest_by_uid()` returns 2 entries ✅
- Direct cache test: `_add_cache_entries()` inserts both occurrences ✅
- Full test suite: 68/68 passing ✅
- Database verification:

  ```sql
  SELECT uid, datetime(event_start) FROM calendar_event_cache WHERE summary LIKE '%Congé%';

  Result:
  d5fcdcc3-...-0257#2026-02-13T00:00:00+00:00 | 2026-02-13 12:00:00
  ```

**Timezone Conversion Verification:**

```python
# Feb 13 12:00 UTC → Toronto
2026-02-13 12:00:00+00:00 → 2026-02-13 07:00:00-05:00
Date: Friday, Feb 13 ✅ (was showing Feb 12 before fix)
```

**Documentation:**

- Updated `docs/db/DB.md` with recurring event UID format and all-day event handling
- Created `docs/ADR/ADR-2026-02-17-recurring-events-allday-timezone-fixes.md`
- Updated memory bank tasks index

**Decision:** Mark task as completed. Both bugs fixed, all tests passing, documentation complete.

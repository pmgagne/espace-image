# ADR-2026-02-12: Backend UTC Time Storage and API Response

**Status:** Accepted
**Date:** 2026-02-12
**Context:**
Espace-Image manages events, alarms, and calendar data across multiple time zones. Consistent handling of time-related information is critical for reliable scheduling, integration, and user experience. Previous implementations mixed local and UTC times, leading to ambiguity and errors. Project documentation and recent ADRs highlight the need for a clear, unified approach.

**Decision:**

- All time-related information (event times, alarm times, calendar entries) is stored in the backend database in UTC (ISO 8601 format).
- The original IANA timezone name is preserved in the `event_tz` field of `CalendarElement` for recurrence expansion and display.
- API responses serialize datetimes as ISO 8601. When `event_tz` is present, the offset is calculated from the original timezone (e.g., `2026-02-17T10:00:00-05:00`); otherwise UTC is returned (e.g., `2026-02-17T15:00:00+00:00`).
- The frontend can parse these ISO 8601 strings directly without additional timezone conversion.

**Consequences:**

- Eliminates ambiguity and errors caused by mixed time zones.
- Simplifies backend logic and API contracts.
- Frontend must handle timezone conversion for all user-facing time values.
- Documentation and tests must reflect UTC storage and API response patterns.

**References:**

---
**iCalendar Parsing Clarification:**

- As of 2026-02-10, all calendar event and alarm parsing uses the [`icalevents`](https://icalevents.readthedocs.io/en/latest/) library (see [TASK011-migrate-icalendar-to-icalevents.md](../../memory-bank/tasks/TASK011-migrate-icalendar-to-icalevents.md)).
- All event and alarm times are normalized to UTC before storage, regardless of original timezone or floating status.
- When parsing iCalendar (ICS) data, if event/alarm times lack a timezone (no TZID or UTC "Z" suffix), the backend treats the datetime as "floating" and interprets it in the backend's local timezone before converting to UTC for storage and API responses.

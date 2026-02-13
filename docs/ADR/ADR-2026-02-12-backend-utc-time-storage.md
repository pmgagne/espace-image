# ADR-2026-02-12: Backend UTC Time Storage and API Response

**Status:** Proposed
**Date:** 2026-02-12
**Context:**
Espace-Image manages events, alarms, and calendar data across multiple time zones. Consistent handling of time-related information is critical for reliable scheduling, integration, and user experience. Previous implementations mixed local and UTC times, leading to ambiguity and errors. Project documentation and recent ADRs highlight the need for a clear, unified approach.

**Decision:**

- All time-related information (event times, alarm times, calendar entries) is stored in the backend database in UTC (ISO 8601 format).
- All API responses from the backend provide time values in UTC.
- The frontend is responsible for converting UTC times to the user's local time zone for display and interaction.
- No local time or timezone-specific values are stored or transmitted by the backend.

**Consequences:**

- Eliminates ambiguity and errors caused by mixed time zones.
- Simplifies backend logic and API contracts.
- Frontend must handle timezone conversion for all user-facing time values.
- Documentation and tests must reflect UTC storage and API response patterns.

**References:**

---
**iCalendar Parsing Clarification:**
When parsing iCalendar (ICS) data, event and alarm times may not always specify a timezone (no TZID or UTC "Z" suffix). In such cases, the backend must treat the datetime as "floating" and interpret it in the backend's local timezone before converting to UTC for storage and API responses.

# ADR-2026-05-01: Calendar Timezone Metadata and Recurrence Handling

## Status
Accepted

## Context
Calendar events are ingested from ICS feeds, which may include timezone identifiers (TZID) and recurrence rules. Past refactors have changed how timezones and all-day events are stored and expanded.

## Decision
- The original event timezone identifier (TZID) is preserved in the `event_tz` field of `CalendarEventCache`.
- All event and alarm times are stored in UTC, but recurrence expansion and display logic must reference the original TZID when present.
- All-day events are stored as date-safe (not timezone-shifted) to avoid off-by-one errors.
- Recurrence expansion must use the event's original timezone for correct wall-clock behavior across DST transitions.

## Consequences
- Downstream consumers (UI, alarms) can reliably reconstruct the intended event time and recurrence.
- Any code that expands or displays events must use the `event_tz` field when present.

## Supersedes
- Any prior practice of discarding or ignoring original event timezones.

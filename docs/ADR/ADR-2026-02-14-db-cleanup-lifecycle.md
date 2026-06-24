---
title: "ADR-2026-02-14: Database Cleanup & Lifecycle for Calendar Events and Alarms"
date: 2026-02-14
status: Accepted


# Architectural Decision Record: Database Cleanup & Lifecycle

## Context

The Espace-Image system caches calendar events and tracks alarm dismissals to support dashboard and slideshow alarm displays. To maintain performance and avoid unnecessary data growth, the database must regularly purge old or irrelevant events and alarms.


## Decision

Cleanup and lifecycle rules now rely on robust event/recurrence expansion and alarm logic provided by the [`icalevents`](https://icalevents.readthedocs.io/en/latest/) library (see [TASK011-migrate-icalendar-to-icalevents.md](../../memory-bank/tasks/TASK011-migrate-icalendar-to-icalevents.md)), with all event and alarm times normalized to UTC (see [ADR-2026-02-12-backend-utc-time-storage.md](ADR-2026-02-12-backend-utc-time-storage.md)).

We implement the following cleanup and lifecycle rules:

### CalendarElement (table: `calendar_elements`)
- Events are cached for a rolling 1-week window.
- On each calendar sync, events that no longer overlap the current window or are removed from the source calendar are purged from the cache.

### AlarmEvent
- Past alarm/event rows whose `trigger_time` is older than the retention window
  (`ALARM_RETENTION_DAYS`, default 30 days) are purged on each background sync,
  regardless of dismissal state. Implemented by `AlarmsService.purge_old_alarms`,
  invoked from `background_sync_calendars` after `general_sync`.
- Dismissed alarms older than the same retention window are also purged by
  `AlarmsService.purge_old_dismissed_alarms` (invoked at alarm-widget render time).
- Active (not dismissed) alarms for current and future events remain in the DB;
  only past rows beyond the retention window are removed.

## Rationale

- **Performance:** Keeps the database lean and fast by retaining only relevant events and alarms.
- **Correctness:** Ensures alarms are only shown for current, active events.
- **Maintainability:** Prevents data bloat and simplifies queries for alarm display.

## Consequences

- **Pros:**
    - Efficient storage and fast queries.
    - No stale alarms or events cluttering the UI or DB.
- **Cons:**
    - Requires careful sync logic to avoid accidental purging of relevant events.
    - If calendar sources are unreliable, events may be purged prematurely.


## Related Decisions

- [ADR-2026-02-14-alarm-dataflow.md](ADR-2026-02-14-alarm-dataflow.md): Alarm display architecture and backend-driven dataflow
- [ADR-2026-02-12-backend-utc-time-storage.md](ADR-2026-02-12-backend-utc-time-storage.md): Time handling rationale and UTC normalization
- [TASK011-migrate-icalendar-to-icalevents.md](../../memory-bank/tasks/TASK011-migrate-icalendar-to-icalevents.md): Migration details and rationale for icalevents
- [DB.md](../db/DB.md): Database schema, alarm/event caching, and usage patterns

---

---
title: "ADR-2026-02-14: Database Cleanup & Lifecycle for Calendar Events and Alarms"
date: 2026-02-14
status: Accepted

# Architectural Decision Record: Database Cleanup & Lifecycle

## Context

The Espace-Image system caches calendar events and tracks alarm dismissals to support dashboard and slideshow alarm displays. To maintain performance and avoid unnecessary data growth, the database must regularly purge old or irrelevant events and alarms.

## Decision

We implement the following cleanup and lifecycle rules:

### CalendarEventCache
- Events are cached for a rolling 1-week window.
- On each calendar sync, events that no longer overlap the current window or are removed from the source calendar are purged from the cache.

### AlarmEvent
- Dismissed alarms older than 30 days are purged.
- After each calendar sync, dismissed alarms outside the current window are also purged.
- Active (not dismissed) alarms for events still present in the calendar remain in the DB.
- Past alarms are only removed if dismissed or if the event is removed from the source calendar.

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

- See [ADR-2026-02-14-alarm-dataflow.md](ADR-2026-02-14-alarm-dataflow.md) for alarm display architecture.
- See [ADR-2026-02-12-backend-utc-time-storage.md](ADR-2026-02-12-backend-utc-time-storage.md) for time handling rationale.

---

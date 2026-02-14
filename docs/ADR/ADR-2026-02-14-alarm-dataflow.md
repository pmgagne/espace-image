---
title: "ADR-2026-02-14: Alarm Display Dataflow Pattern"
date: 2026-02-14
status: Accepted

# Architectural Decision Record: Alarm Display Dataflow Pattern

## Context

The Espace-Image system displays calendar-driven alarms on a dashboard and slideshow UI. The backend fetches and parses calendar feeds (ICS/webcal), determines which events are relevant for the current "attention window," and exposes alarms to the frontend via HTML fragments. The frontend is responsible only for rendering these fragments, not for any alarm logic.

## Decision

We adopt a backend-driven dataflow for alarm display, with the following steps:

1. **Calendar Sync (Background)**
    - The backend's `CalendarService` periodically fetches ICS/webcal feeds (URLs stored in the database).
    - Events are parsed and filtered to retain only those within the configured attention window (e.g., next 24h).
    - These events are cached in the database for fast access.

2. **Alarm Extraction (On Request)**
    - When the frontend requests the alarm list (e.g., via `/admin/partials/alarms` or `/components/alarms`), the backend queries the cached events.
    - The `AlarmService` applies alarm logic (e.g., filtering, deduplication, formatting) to produce the list of alarms for display.

3. **Template Rendering**
    - The backend renders a Jinja2 HTML fragment (e.g., `alarms.html`) containing the alarms.
    - This fragment is returned to the frontend.

4. **Frontend Display**
    - The frontend (HTMX or browser) injects the HTML fragment into the DOM.
    - No client-side alarm logic is performed; the frontend simply displays the provided alarms.

5. **Updates**
    - The frontend may poll or use HTMX to refresh the alarm list periodically, triggering a new backend fetch and render.

## Diagram

```mermaid
flowchart TD
    subgraph Backend
        A[CalendarService\nFetch ICS/webcal] --> B[Parse events\nFilter by attention window]
        B --> C[Cache events\nin DB]
        C --> D[AlarmService\nQuery & format alarms]
        D --> E[Render alarms.html\n(Jinja2 partial)]
    end

    subgraph Frontend
        F[HTMX/Browser\nrequests alarms partial] --> E
        E --> G[Inject HTML\nDisplay alarms]
        G --> H[Periodic refresh\nvia HTMX/polling]
        H --> F
    end

    style Backend fill:#f9f,stroke:#333,stroke-width:1px
    style Frontend fill:#bbf,stroke:#333,stroke-width:1px
```

## Rationale

- **Separation of concerns:** Backend handles all alarm logic; frontend is a pure display layer.
- **Performance:** Only relevant events are cached; no heavy parsing at request time.
- **Security/Correctness:** Centralized alarm logic avoids client-side bugs or drift.
- **Flexibility:** Alarm rules and event sources can change without frontend changes.
- **Maintainability:** All business logic is testable in Python.

## Consequences

- **Pros:**
    - Robust, scalable, and easy to maintain.
    - Efficient for current and foreseeable event volumes.
    - Supports both admin and slideshow UIs with minimal duplication.
- **Cons:**
    - Real-time push (e.g., instant alarm updates) would require additional mechanisms (WebSockets/SSE).
    - If event volume grows dramatically, further caching or async job processing may be needed.

## Related Decisions

- See ADR-2026-02-12-backend-utc-time-storage.md for time handling rationale.

---

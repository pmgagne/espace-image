# TASK011 - Migrate from icalendar to icalevents

**Status:** Pending
**Added:** 2026-02-10
**Updated:** 2026-02-10

## Original Request

Replace the use of the icalendar library with the icalevents library (<https://icalevents.readthedocs.io/en/latest/>) for calendar event parsing and handling throughout the project.

## Thought Process

- icalevents provides a higher-level API for parsing and iterating over iCalendar events, including recurrence, which simplifies code and improves maintainability.
- Migrating will require identifying all usages of icalendar, updating code to use icalevents, and ensuring all features (recurrence, alarms, etc.) are preserved.
- Documentation and tests must be updated to reflect the new dependency and API.

## Implementation Plan

- Audit the codebase for all icalendar usages (imports, parsing, event handling).
- Update requirements to add icalevents and remove icalendar.
- Refactor calendar service and related logic to use icalevents.
- Update or add tests for calendar parsing and recurrence.
- Update documentation to reflect the new library and usage patterns.
- Validate all calendar features in the app.

## Progress Tracking

**Overall Status:** Not Started - 0%

### Subtasks

| ID  | Description                                         | Status      | Updated    | Notes |
|-----|-----------------------------------------------------|-------------|------------|-------|
| 11.1 | Audit codebase for icalendar usage                  | Not Started |            |       |
| 11.2 | Update requirements: add icalevents, remove icalendar| Not Started |            |       |
| 11.3 | Refactor calendar service to use icalevents         | Not Started |            |       |
| 11.4 | Update/add tests for calendar parsing/recurrence    | Not Started |            |       |
| 11.5 | Update documentation for new library                | Not Started |            |       |
| 11.6 | Validate all calendar features                      | Not Started |            |       |

## Progress Log

### 2026-02-10

- Task created, plan and subtasks defined.

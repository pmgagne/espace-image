# Active Context

**Last Updated**: 2026-02-19

## Current Work Focus

### Recently Completed (2026-02-19)

**Security Audit and Code Quality Improvements**:

1. Fixed critical alarm display bug (alarms showing before trigger time)
2. Fixed dismiss button functionality (HTMX attributes)
3. Conducted comprehensive security audit (13 issues identified and fixed)
4. Eliminated code anti-patterns (triple-nested try/except blocks)
5. Added magic byte validation for image uploads
6. Protected debug endpoints with environment gate
7. Sanitized error messages to prevent credential leakage
8. Updated all documentation to reflect icalevents migration

9. Verified DB schema and documentation are current (see docs/db/DB.md)

See [ADR-2026-02-19-security-audit-code-quality.md](../docs/ADR/ADR-2026-02-19-security-audit-code-quality.md) for complete details.

### Documentation Synchronization (2026-02-19)

- Created missing memory-bank core files (projectbrief.md, productContext.md, etc.)
- Fixed outdated icalendar references in .specs/codebase/ (STACK.md, INTEGRATIONS.md, ARCHITECTURE.md)
- Created ADR documenting security audit
- Verified all ADRs reflect current architecture

## Recent Changes

### Alarm System (2026-02-17)

Fixed two critical bugs in calendar event caching:

1. **Recurring Event Deduplication**: Biweekly events only showing one occurrence
   - Root cause: Shared UID across occurrences triggered deduplication logic
   - Solution: Composite UID format `{original_uid}#{occurrence_iso}` for each occurrence
   - ADR: [ADR-2026-02-17-recurring-events-allday-timezone-fixes.md](../docs/ADR/ADR-2026-02-17-recurring-events-allday-timezone-fixes.md)

2. **All-Day Event Timezone Shift**: Events displaying on wrong day in negative UTC offset timezones
   - Root cause: icalevents returns midnight UTC, converted to previous day in America/Toronto (UTC-5)
   - Solution: Track `all_day` flag, preserve date without timezone conversion
   - Result: All-day events now display on correct calendar date

3. **DB Schema Review**: Confirmed all tables (AppSettings, Preset, Photo, CalendarSource, CalendarEventCache, AlarmEvent, CalendarSyncStatusEntry) are up to date and relationships are correct. All event/alarm times stored in UTC, original timezone preserved for display/recurrence.

### ical events Migration (2026-02-10)

Migrated from `icalendar` to `icalevents` library:

- Simplified recurrence handling (RRULE expansion handled by library)
- Improved VALARM parsing and alarm extraction
- Better timezone handling for recurring events
- See [TASK011-migrate-icalendar-to-icalevents.md](tasks/TASK011-migrate-icalendar-to-icalevents.md)

## Next Steps

### Immediate Priorities

1. **Monitor Production**: Verify alarm display works correctly after fixes
2. **Performance Testing**: Ensure no degradation from security changes
3. **User Acceptance**: Confirm dismiss button and alarm timing work as expected

### Short-Term Improvements

1. **Test Coverage**: Add tests for new security validations
2. **Error Logging**: Expand logging for calendar sync failures
3. **Documentation**: Update user guide with calendar setup instructions
4. **CI/CD**: Verify GitHub Actions pipeline passes with all changes

### Medium-Term Enhancements

1. **CSRF Protection**: Implement if authentication is added
2. **Redis Rate Limiting**: Replace in-memory limiter for multi-worker deployments
3. **Metrics Dashboard**: Track calendar sync success rate, alarm accuracy
4. **Backup/Restore**: Add import/export for settings and calendar sources

### Long-Term Considerations

1. **Authentication Layer**: Optional OAuth2 for external network exposure
2. **Mobile App**: Native iOS/Android app to complement PWA
3. **Multi-Tenant**: Support multiple families/users with isolated data
4. **Cloud Sync**: Optional cloud backup for photos and settings

## Active Decisions

### Architectural

- **No authentication remains acceptable** for internal network deployment
- **SQLite is sufficient** for single-family use case (no need for PostgreSQL)
- **HTMX UI approach validated** — simpler than React/Vue for this use case
- **Dual UI strategy working well** — modern and legacy modes coexist cleanly

- **SQLModel ORM and UTC time storage**: Continue using SQLModel for DB access and UTC for all timestamps. Schema and cleanup patterns validated as robust for current/future needs.

### Technical

- **icalevents library proven stable** after 2+ weeks of production use
- **Magic byte validation balances security vs. complexity** — good middle ground
- **UTC time storage best practice** — eliminates timezone bugs
- **Service layer pattern beneficial** — calendar/weather/image logic well-encapsulated

### Process

- **Security-first mindset adopted** — audit revealed value of proactive review
- **ADR documentation valuable** — aids AI agent continuity across sessions
- **Test-driven validation essential** — caught regression from error message changes
- **Linter automation helpful** — ruff caught subtle code quality issues

## Context for AI Agents

### Code Patterns to Follow

1. **Always escape HTML in templates** — use `markupsafe.escape()` or Jinja2 auto-escaping
2. **Validate all URIs** — check scheme and structure before external calls
3. **Path canonicalization mandatory** — use `Path.resolve().is_relative_to()` for file operations
4. **UTC time storage rule** — all timestamps stored with `datetime.now(UTC)` or `timezone.utc`
5. **No triple-nested try/except** — single try/except with meaningful fallback only

### Common Pitfalls to Avoid

1. **Don't duplicate JavaScript** between inline `<script>` and external .js files
2. **Don't swallow own ValueError** in exception handlers (use `except ValueError: raise`)
3. **Don't trust user input** for file paths, UIDs, URLs (validate/sanitize)
4. **Don't use deprecated timezone APIs** (`pytz` for timezones, not `dateutil`)
5. **Don't skip reading files before editing** — always Read before Edit/Write

### Project-Specific Conventions

- Routes in `app/routers/` use `async def` and `Depends(get_session)`
- Services in `app/services/` use static methods
- Templates in `app/templates/` use Jinja2 auto-escaping
- Tests in `tests/` use pytest with FastAPI TestClient
- ADRs in `docs/ADR/` document all architectural decisions

## Related Documents

- [systemPatterns.md](systemPatterns.md) — Technical patterns and design decisions
- [progress.md](progress.md) — Feature completion status
- [tasks/_index.md](tasks/_index.md) — Task tracking and history

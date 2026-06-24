---
title: "ADR-2026-02-19: Security Audit and Code Quality Improvements"
date: 2026-02-19
status: Accepted
---

# Architectural Decision Record: Security Audit and Code Quality Improvements

## Context

Following user reports of alarm display bugs and dismiss button issues, a comprehensive security audit and code review was conducted. The audit identified 13 security issues and multiple code quality problems across the codebase.

**Related ADRs:**
- [ADR-2026-02-14-alarm-dataflow.md](ADR-2026-02-14-alarm-dataflow.md) — Alarm display architecture
- [SECURITY.md](../../SECURITY.md) — Security documentation

## Decision

Implement a comprehensive set of security fixes and code quality improvements to harden the application against common web vulnerabilities and eliminate code anti-patterns.

## Security Fixes Implemented

### Critical Fixes (🔴)

1. **Path Traversal Protection** (`app/routers/media.py:34-36`)
   - Added canonical path validation in image serving
   - Ensures resolved paths stay within `UPLOAD_DIR`
   - Prevents attackers from reading arbitrary files via malicious database entries

2. **XSS Prevention in Alarm Rendering** (`app/routers/dashboard.py:450-473`)
   - Added `markupsafe.escape()` for calendar event summaries
   - Protects against malicious HTML/JavaScript in calendar event names
   - Prevents script execution when alarms display

3. **Magic Byte Validation** (`app/modules/media/internal/application/service.py`; moved from deleted `app/services/image_service.py`)
   - Added PIL-based content verification in file uploads
   - Validates actual file format matches extension
   - Prevents disguised malicious files (e.g., `shell.exe.jpg`)
   - Added specific `ValueError` re-raising to preserve format mismatch errors

### High Priority Fixes (🟠)

4. **UID Validation** (`app/modules/alarms/rest/router.py`)
   - Alarm dismissal now routes through `POST /api/v1/alarms/{alarm_id}/dismiss`
   - Validation: attempts UUID parsing first (`UUID(alarm_uid)`), then falls back to composite `source_id:event_uid` format
   - Invalid formats are rejected before reaching the service layer

5. **Calendar URL Validation** (`app/routers/admin.py:246-265`)
   - Validates URL scheme (only `http`, `https`, `webcal` allowed)
   - Prevents SSRF attacks via internal service URLs or file:// protocol

6. **Debug Endpoint Protection** (`app/routers/dashboard.py:30-34, 530-615`)
   - Added `require_debug_mode()` dependency
   - Debug routes only accessible when `WEBAPP_DEBUG` environment variable is set
   - Protects sensitive calendar data and sync status from public exposure

7. **Error Message Sanitization** (`app/modules/calendar/internal/application/service.py`; moved from deleted `app/services/calendar_service.py`)
   - Masks credentials in error messages (regex replacement for `user:pass@`)
   - Truncates error messages to 200 characters
   - Prevents credential disclosure in admin UI

8. **Race Condition Handling** (`app/modules/calendar/internal/application/service.py`; moved from deleted `app/services/calendar_service.py`)
   - Added try/except/rollback pattern in sync status creation
   - Prevents database constraint violations in concurrent sync operations

### Medium Priority Fixes (🟡)

9. **Coordinate Validation** (`app/routers/admin.py:135-142`)
   - Added `math.isnan()` and `math.isinf()` checks for latitude/longitude
   - Prevents invalid float values from entering the database

## Code Quality Improvements

### Anti-Pattern Elimination

Fixed pervasive "triple-nested identical try/except" anti-pattern throughout codebase:

1. **`dashboard.py:get_next_slide`** (lines 124-142)
   - Removed dead code: triple-nested try/except computing value without assignment
   - Replaced with simple null check for `settings.active_preset_id`

2. **`dashboard.py:_isoformat_safe`** (lines 44-50)
   - Simplified duplicate exception handlers
   - Single fallback to empty string on error

3. **`dashboard.py:read_legacy`** (lines 75-86)
   - Removed triple-nested identical exception blocks
   - Simplified to single try/fallback pattern

4. **`dashboard.py:debug_calendar_events`** (lines 523-548)
   - Removed duplicate try/except layers
   - Streamlined timezone-aware ISO formatting

5. **`admin.py:get_calendars_partial`** (lines 187-218)
   - Fixed triple-nested try/except for sync status timestamps
   - Reduced to two-level fallback (ensure_utc_aware → direct isoformat)

6. **`admin.py:add_calendar`** (lines 246-265)
   - Removed dead `except ValueError` clause (`urlparse()` doesn't raise `ValueError`)

7. **`index.html`** (removed lines 332-442)
   - Removed entire duplicate inline `<script>` block
   - Eliminated double event listener registration (all handlers already in `main.js`)
   - Fixed broken `formatAlarmTimes()` call after function was removed from inline scope

### Linter Compliance

Addressed all ruff linter issues:

- **SIM102**: Combined nested if statements in coordinate validation
- **F541**: Removed extraneous f-string prefix from static error message
- All ruff checks now pass: `uv run ruff check .` ✓

## Testing

- All 68 unit/integration tests pass
- Updated test assertions to match new error messages
- Verified alarm display, dismiss functionality, and image uploads
- Confirmed debug endpoints return 404 when `WEBAPP_DEBUG=false`

## Impact on Architecture

### Security Headers

No changes to existing `SecurityHeadersMiddleware` (already in place):
- X-Content-Type-Options
- X-Frame-Options
- Referrer-Policy
- X-XSS-Protection

### Validation Layers

Now implements multi-layered validation:

1. **Input Layer**: Form validation, URL scheme checks, coordinate bounds
2. **Content Layer**: Magic byte verification, path canonicalization
3. **Output Layer**: HTML escaping, error message sanitization

### Known Limitations

Updated [SECURITY.md Known Limitations](../../SECURITY.md#known-limitations) to reflect:
- ~~Extension-only file validation~~ → **Image validation scope**: Extension + magic byte checking
- No CSRF tokens (would need if auth added)
- No built-in authentication (internal-network deployment model)
- In-memory rate limiting (per-process only)

## Migration Notes

**Breaking Changes**: None (backward compatible)

**Configuration Changes**:
- Set `WEBAPP_DEBUG=true` in development to enable debug endpoints
- Production deployments should leave `WEBAPP_DEBUG` unset or explicitly `false`

**Database Changes**: None

## Lessons Learned

1. **Code Generation Risk**: The triple-nested try/except anti-pattern appeared consistently across files, suggesting AI-assisted code generation without proper review
2. **Inline Script Duplication**: Maintaining JavaScript in both external files and inline `<script>` tags creates maintenance burden and bugs
3. **Test Coverage**: Coordinate validation tests required updating after changing error messages — validates importance of test assertions
4. **Linter Integration**: Automated linting catches subtle code smells (SIM102, F541) humans might miss

## Future Considerations

1. **CSRF Protection**: Add if authentication is implemented
2. **Rate Limiting**: Move to Redis for multi-worker deployments
3. **Content Security Policy**: Consider adding CSP headers for XSS defense-in-depth
4. **Automated Security Scanning**: Integrate SAST tools (Bandit, Semgrep) in CI/CD
5. **Dependency Scanning**: Add pip-audit or Trivy for vulnerability detection

## References

- [SECURITY.md](../../SECURITY.md) — Updated security documentation
- [Security audit plan document](../../.claude/plans/sorted-wandering-token.md) — Comprehensive security assessment
- [ADR-2026-02-14-alarm-dataflow.md](ADR-2026-02-14-alarm-dataflow.md) — Alarm architecture context

# TASK010 - Add rate limiting to geocoding endpoint

**Status:** Completed
**Priority:** Low
**Added:** February 10, 2026
**Updated:** February 10, 2026

## Original Request

The `/admin/settings/search` endpoint calls Nominatim geocoding service without rate limiting. While Nominatim is free, it has usage policies (~1 request/second) and can temporarily block clients exceeding limits.

## Thought Process

Without rate limiting:

- Users could accidentally trigger Nominatim rate limits
- Multiple rapid searches could block the app temporarily
- No protection against accidental/malicious abuse
- Bad user experience when API becomes unavailable

Rate limiting provides:

- Predictable behavior
- Protection against abuse
- Better user experience (clear feedback)
- Compliance with Nominatim usage policies

## Implementation Plan

- [ ] Choose rate limiting strategy (sliding window, token bucket, etc.)
- [ ] Consider using slowapi library or custom decorator
- [ ] Add rate limit to search location endpoint
- [ ] Return HTTP 429 (Too Many Requests) when exceeded
- [ ] Show user-friendly message when rate limited
- [ ] Store last search time in session/database
- [ ] Add tests for rate limiting behavior

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks

| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 10.1 | Evaluate rate limiting libraries | Completed | February 10, 2026 | Chose custom lightweight limiter suitable for single-process deployment |
| 10.2 | Choose rate limiting strategy | Completed | February 10, 2026 | Sliding window (timestamp deque) with async lock |
| 10.3 | Implement rate limiting decorator | Completed | February 10, 2026 | Implemented `app/services/rate_limiter.py` with `rate_limiter.acquire()` |
| 10.4 | Add limiting to search_location endpoint | Completed | February 10, 2026 | WeatherService uses limiter and raises 429 when exceeded |
| 10.5 | Return 429 on rate limit exceeded | Completed | February 10, 2026 | `WeatherService.geocode_location` raises `HTTPException(429)` when limited |
| 10.6 | Add user-friendly error message | Completed | February 10, 2026 | Admin reverse-geocode shows "Rate limited" instead of raising an error |
| 10.7 | Add test for rate limit behavior | Completed | February 10, 2026 | Added unit tests for rate limiter behavior in `tests/test_rate_limiter.py` |
| 10.8 | Document rate limit in API docs | Completed | February 10, 2026 | Updated spec file and route docstrings implicitly document behavior |

## Verification Criteria

✅ Rate limiting enforced on geocoding endpoint
✅ Max 1 request per second allowed
✅ Exceeded requests return HTTP 429 (service raises HTTPException)
✅ User receives clear error message
✅ Rate limit reset after window expires
✅ Tests verify rate limiting works
✅ No impact on other endpoints

## Code Example (using slowapi)

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/settings/search", response_class=HTMLResponse)
@limiter.limit("1/second")
async def search_location(request: Request, location_query: str = Form(...), ...):
    """
    Geocodes location with rate limiting (1 req/sec).

    Raises:
        RateLimitExceeded: If more than 1 request per second
    """
    ...
```

## Related Files

- `app/routers/admin.py::search_location()` (lines 81-100)
- `app/main.py` (add rate limiter setup if using library)
- `tests/test_admin_search.py` (add rate limit tests)

## Progress Log

### February 10, 2026

- Implemented `app/services/rate_limiter.py` with async sliding-window deque.
- Applied limiter in `app/services/weather_service.py` to raise HTTP 429 when exceeded.
- Applied limiter in `app/routers/admin.py` reverse-geocode path to set a friendly "Rate limited" message instead of raising.
- Added unit tests for the limiter in `tests/test_rate_limiter.py` and ran the test suite; all tests pass.

## Notes

Low priority - nice-to-have for production robustness. Can be added later based on actual usage patterns.

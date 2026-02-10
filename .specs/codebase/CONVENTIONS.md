# Code Conventions

## Naming Conventions

### Files

**Pattern:** Snake case, descriptive, grouped by layer

Examples from codebase:

- `app/routers/dashboard.py` (feature-based organization)
- `app/services/calendar_service.py` (service encapsulates domain logic)
- `app/db/models.py` (database layer consolidation)
- `test_calendar_integration.py` (test files prefixed with test_)

### Functions/Methods

**Pattern:** Snake case, verb-first for actions, descriptive

Examples:

- `read_root()` (query operation, REST convention)
- `get_weather()` (retrieves data)
- `upload_file()` (modifies state)
- `sync_calendar_events()` (background job)
- `parse_ics()` (parsing/transformation)
- `save_upload()` (storage operation)

Async functions: Same naming, no async prefix

```python
async def read_root(request: Request):  # Not async_read_root
async def background_sync_calendars():
```

### Variables

**Pattern:** Snake case, descriptive, context-appropriate

Examples:

- `user_agent = request.headers.get("user-agent", "")`
- `calendar_sources = session.exec(select(CalendarSource)).all()`
- `weather_latitude`, `weather_longitude` (compound names for related concepts)
- `active_preset_id` (id suffix for database identifiers)
- `trigger_time`, `dismissed_at` (verb forms for timestamps)

### Constants

**Pattern:** Upper snake case, module-level

Examples from observed code:

```python
LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING").upper()
DEBUG_MODE = os.getenv("WEBAPP_DEBUG", "").lower() in ("true", "1", "yes")
```

Database connection strings, config paths: Follow same pattern

### Classes

**Pattern:** PascalCase, noun-based (entities or services)

Examples:

- `CalendarService` (service class)
- `GalleryManager` (manager class)
- `WeatherService` (service class)
- `Preset`, `Photo`, `AlarmEvent` (model classes)
- `CalendarSyncStatus` (enum)

## Code Organization

### Import/Dependency Declaration

**Order (observed):**

1. Stdlib imports (datetime, logging, os, etc.)
2. Third-party imports (fastapi, httpx, sqlmodel, etc.)
3. Blank line
4. Local application imports (app.*)

**Example from admin.py:**

```python
import asyncio
import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.db.engine import engine
from app.db.models import (...)
from app.db.session import get_session
from app.services.calendar_service import CalendarService
```

### File Structure

**Pattern:** Consistent within routers and services

Typical router structure:

1. Imports
2. Router instantiation: `router = APIRouter(...)`
3. Templates setup: `templates = Jinja2Templates(...)`
4. Manager/service instantiation: `gallery_manager = GalleryManager()` (if needed)
5. Route handlers (organized by feature/logical flow)

Typical service structure:

1. Imports
2. Logger setup: `logger = logging.getLogger(__name__)`
3. Service class with static methods or instance methods
4. Helper functions/methods organized by responsibility

## Type Safety/Documentation

**Approach:** Type hints used throughout (Pyright strict mode)

Examples:

```python
async def read_root(request: Request, session: Session = Depends(get_session)):
    # Type hints on parameters, return inferred or explicit

async def get_weather(session: Session = Depends(get_session)) -> HTMLResponse:
    # Explicit return type for response handlers

def parse_ics(ics_content: str) -> Calendar | None:
    # Union types using | operator (Python 3.10+ syntax)

trigger_time: datetime
dismissed_at: datetime | None
```

**Docstrings:** Module and complex function docstrings present; style is brief

Example:

```python
def parse_ics(ics_content: str) -> Calendar | None:
    """Parses ICS content string into a Calendar object."""
    try:
        return Calendar.from_ical(ics_content)
```

## Error Handling

**Pattern:** Pragmatic error catching with logging

Observed approach:

```python
try:
    # Attempt operation (e.g., geocoding, ICS fetch)
    resp = await client.get(url, headers=...)
    data = resp.json()
except Exception as e:
    logger.exception(f"Error in {operation}: {e}")
    # Graceful fallback: return empty result, skip step, or raise HTTPException
    return templates.TemplateResponse(...)  # with default values
```

Background jobs suppress exceptions:

```python
async def background_sync_calendars():
    try:
        await CalendarService.sync_calendar_events(session)
    except Exception as e:
        logger.exception(f"Error in background calendar sync: {e}")
    finally:
        session.close()
```

HTTPException for user-facing errors:

```python
if not settings or not settings.active_preset_id:
    return "<div class='error-msg'>No Preset Active...</div>"  # HTML error fragment
```

## Comments/Documentation

**Style:** Minimal inline comments; code should be self-documenting

Observed approach:

- Docstrings on functions/classes (brief, purpose-focused)
- Comment above complex logic blocks (e.g., "Auto-redirect for iPad 2")
- Debug print statements for development (e.g., `print(f"DEBUG: Incoming User-Agent: {user_agent}")`)
- Not over-commented; relies on clear naming

Example:

```python
# Auto-redirect for iPad 2 (iOS 9)
if "ipad" in user_agent and "os 9" in user_agent:
    return RedirectResponse(url="/legacy", status_code=302)
```

## Patterns & Best Practices

### FastAPI Routes

- Use `Depends(get_session)` for DB access
- Return `TemplateResponse` for HTML; `JSONResponse` for data; `HTMLResponse` for fragments
- Route handlers are async-first
- Prefix admin routes: `@router.get("/admin/...")`

### Service Methods

- Static methods for stateless operations (easier to test, no instance state)
- Logging at key points (retry attempts, failures, sync completion)
- Exponential backoff for external API calls (httpx + backoff library)

### Database Access

- Use SQLModel with `select()` for queries
- Always close sessions (handled by dependency injection cleanup)
- Unique constraints on business-critical fields (e.g., calendar event UIDs)

### Testing

- Use fixtures for session and client setup
- Mock external dependencies (@patch decorators)
- Test in-memory SQLite (StaticPool for thread safety)
- Test names follow pattern: `test_{feature}_{scenario}`

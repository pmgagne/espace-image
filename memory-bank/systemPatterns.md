# System Patterns — Espace-Image

**Extracted from**: `.specs/codebase/ARCHITECTURE.md` and production codebase analysis

## Architecture Overview

**Pattern**: Monolithic layered architecture with service layer + background jobs

**Database Layer**: SQLite (single-file) with SQLModel ORM. All business entities (photos, presets, calendar sources, events, alarms, sync status) are modeled as SQLModel classes with relationships. All timestamps are stored in UTC. Schema is optimized for fast event, alarm, and photo lookups.

### Core Layers

```
Presentation Layer (Routers)
    ↓
Service Layer (Business Logic)
    ↓
Data Layer (SQLModel ORM)
    ↓
Storage (SQLite + File System)

**DB Schema**: See docs/db/DB.md for full schema. Key tables: AppSettings, Preset, Photo, CalendarSource, CalendarEventCache, AlarmEvent, CalendarSyncStatusEntry. Relationships: Preset 1--* Photo, CalendarSource 1--* CalendarEventCache, CalendarSource 1--1 CalendarSyncStatusEntry.
```

## Design Patterns

### 1. Service Layer Pattern

**Implementation**: Static methods in dedicated service classes

**Location**: `app/services/`

**Services**:

- `CalendarService`: ICS fetching, event caching, alarm extraction
- `ImageService`: Photo optimization, gallery management
- `WeatherService`: Open-Meteo API integration, geocoding
- `AlarmService`: Alarm formatting, dismissal tracking, cleanup

**Benefits**:

- Business logic isolated from HTTP concerns
- Testable without FastAPI dependencies
- Reusable across multiple route handlers
- Clear separation of concerns

**Example**:

```python
# Router calls service
@router.post("/calendars/sync-now")
async def sync_calendars_now(session: Session = Depends(get_session)):
    await CalendarService.sync_calendar_events(session)
    return await get_calendars_partial(request, session)
```

### 2. Dependency Injection Pattern

**Implementation**: FastAPI `Depends()` for database sessions

**Location**: `app/db/session.py`

**Benefits**:

- Automatic session lifecycle management
- Testable (can inject mock sessions)
- No global state
- Transaction boundaries clear

**Example**:

```python
@router.get("/")
async def read_root(
    request: Request,
    session: Session = Depends(get_session)
):
    settings = session.exec(select(AppSettings)).first()
    # session automatically committed/rolled back
```

### 3. HTMX Fragment Pattern

**Implementation**: Routes return HTML fragments via `TemplateResponse`

**Location**: `app/routers/admin.py`, `app/templates/partials/`

**Benefits**:

- No client-side state management
- Minimal JavaScript complexity
- Progressive enhancement
- Server-side rendering

**Example**:

```python
@router.post("/presets")
async def create_preset(name: str = Form(...), session: Session = Depends(get_session)):
    preset = Preset(name=name)
    session.add(preset)
    session.commit()
    # Return updated gallery partial (HTMX swaps content)
    return await get_gallery_partial(request, preset.id, session)
```

### 4. Dual UI Strategy Pattern

**Implementation**: User-Agent detection + conditional templates

**Location**: `app/routers/dashboard.py`

**Decision Points**:

- **Auto-detect**: User-Agent `"ipad"` + `"os 9"` → redirect to `/legacy`
- **Modern UI**: ES6 JavaScript, CSS Grid, HTMX
- **Legacy UI**: ES5 JavaScript, basic CSS, XHR (no HTMX)

**Benefits**:

- Maximum hardware compatibility
- Graceful degradation
- Single codebase, dual frontendsevidence

### 5. Background Job Scheduling Pattern

**Implementation**: APScheduler with async coordinator

**Location**: `app/main.py` lifespan context

**Jobs**:

- Calendar sync: every 3 hours (configurable)
- Unified index refresh (weather + alarms): every 5 minutes (configurable, via `/components/index-refresh`)
- (Future): Photo rotation, cleanup tasks

**Pattern**:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: register jobs
    scheduler.add_job(background_sync_calendars, "interval", minutes=CALENDAR_SYNC_INTERVAL_MINUTES)
    # Unified index refresh interval is exposed to templates for UI polling
    scheduler.start()
    yield
    # Shutdown: graceful stop
    if scheduler.running:
        scheduler.shutdown()
```

### 6. Repository-Like Data Access

**Implementation**: SQLModel declarative models with relationships

**Location**: `app/db/models.py`

**Pattern**: Define models with relationships, query via SQLModel ORM

**Benefits**:

- Type-safe queries (Pydantic validation)
- Automatic schema generation
- Clear relationship mapping
- Testable with in-memory SQLite

**DB Usage Patterns**:

- Always use UTC-aware datetimes for event and alarm logic.
- Use composite UIDs (source_id:uid) for event/alarms to namespace across sources.
- Purge old dismissed alarms and stale events to keep DB lean.
- Use relationships for efficient photo/event lookup.

**Example**:

```python
class Preset(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    photos: list["Photo"] = Relationship(back_populates="preset")

# Query with relationships
preset = session.get(Preset, preset_id)
photos = preset.photos  # Lazy-loaded via relationship
```

### 7. Template-Based HTML Rendering

**Implementation**: Jinja2 with auto-escaping enabled

**Location**: `app/templates/`

**Security**: HTML auto-escaped by default (XSS protection)

**Pattern**:

```jinja2
{# Auto-escaped by default #}
<span class="alarm-title">{{ alarm.name }}</span>

{# Manual escape for Python f-strings #}
from markupsafe import escape
html = f"<span>{escape(user_input)}</span>"
```

### 8. UTC Time Normalization

**Implementation**: All database timestamps in UTC, convert for display

**Location**: `app/utils/timezone.py`, all services

**Benefits**:

- No timezone bugs
- Unambiguous time comparisons
- Display timezone conversion happens at template layer

**Pattern**:

```python
# Storage: always UTC
event.event_start = ensure_utc_aware(datetime.now())

# Display: convert to local or original timezone
display_time = datetime_to_iso_with_tz(event.event_start, event.event_tz)
```

**DB Cleanup**:

- CalendarEventCache: Rolling 1-week window, purged on sync.
- AlarmEvent: Dismissed alarms >30 days old are purged.
- Photos: Orphaned photos (no preset) are cleaned up by admin tools.

### 9. Retry with Exponential Backoff

**Implementation**: `@backoff.on_exception()` decorator

**Location**: `app/services/calendar_service.py`

**Pattern**:

```python
@backoff.on_exception(
    backoff.expo,
    httpx.HTTPError,
    max_tries=5,
    max_time=30,
)
async def _fetch_ics_content(url: str) -> str:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text
```

## Component Relationships

### Data Flow: Calendar Sync

```
APScheduler (10 min interval)
    ↓
CalendarService.sync_calendar_events()
    ├─ Fetch all CalendarSource URLs
    ├─ Parse events with icalevents
    ├─ Extract alarms (VALARM entries)
    ├─ Cache events in CalendarEventCache
    ├─ Create AlarmEvent records
    └─ Update CalendarSyncStatusEntry

Dashboard route: GET /components/alarm
    ↓
_fetch_calendar_alarms()
    ├─ Query CalendarEventCache (1-week window)
    ├─ Filter by trigger_time <= now
    ├─ Check for dismissed AlarmEvent records
    └─ Return active alarms

AlarmService.format_alarms()
    ├─ Convert UTC times to display timezone
    ├─ Generate fallback text (French weekday/date)
    └─ Render alarms.html template

Frontend (HTMX)
    ├─ Poll GET /components/alarm every 10 seconds
    ├─ Swap #alarm-poller innerHTML
    └─ Format timestamps via JavaScript (client timezone)
```

### Data Flow: DB Cleanup

```
APScheduler (scheduled intervals)
    ↓
AlarmService.cleanup_old_alarms()
    └── Purge AlarmEvent records >30 days old
CalendarService.cleanup_stale_events()
    └── Purge CalendarEventCache entries outside 1-week window
Admin tools
    └── Remove orphaned Photo records/files
```

### Data Flow: Image Upload

```
Admin: POST /admin/upload
    ↓
Router: upload_photos()
    ├─ Validate file extension (.jpg, .png, .heic)
    ├─ Verify magic bytes (PIL image validation)
    └─ Call GalleryManager.save_upload()
        ├─ Optimize image (resize, JPEG conversion)
        ├─ Generate filename (UUID + timestamp)
        ├─ Save to data/uploads/{preset_name}/
        └─ Create Photo database record

Gallery partial refresh
    ↓
HTMX swaps updated gallery HTML
```

## Security Patterns

### 1. Input Validation Layers

- **Form Layer**: FastAPI Form() validation
- **Content Layer**: Magic byte verification (PIL), path canonicalization
- **Output Layer**: HTML escaping, error message sanitization

### 2. SSRF Prevention

- URL scheme whitelist (`http`, `https`, `webcal` only)
- No `file://`, `gopher://`, or internal service URLs
- Implemented in `app/routers/admin.py:add_calendar`

### 3. Path Traversal Prevention

- Canonical path validation with `Path.resolve().is_relative_to()`
- All file operations verify paths stay within `UPLOAD_DIR`
- Implemented in `app/routers/media.py`

### 4. XSS Prevention

- Jinja2 auto-escaping for all templates
- Manual `markupsafe.escape()` for generated HTML
- Implemented in `app/routers/dashboard.py:_render_alarm_item`

## Testing Patterns

### Unit Test Structure

**Location**: `tests/`

**Pattern**: FastAPI TestClient + in-memory SQLite + pytest fixtures

**Example**:

```python
@pytest.fixture
def session():
    # In-memory database per test
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_example(client, session):
    # Arrange
    preset = Preset(name="Test")
    session.add(preset)
    session.commit()

    # Act
    response = client.get("/admin/partials/gallery")

    # Assert
    assert response.status_code == 200
```

## Related Documents

- [.specs/codebase/ARCHITECTURE.md](../.specs/codebase/ARCHITECTURE.md) — Detailed architecture reference
- [activeContext.md](activeContext.md) — Current development focus
- [techContext.md](techContext.md) — Technology stack and setup

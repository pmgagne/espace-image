# Architecture

**Pattern:** Monolithic layered architecture with service layer + background jobs

## High-Level Structure

```
FastAPI Application (app/main.py)
    ├── Routers (app/routers/)
    │   ├── dashboard.py      → Slideshow views (modern & legacy)
    │   ├── media.py          → Photo/gallery endpoints
    │   └── admin.py          → Admin UI with HTMX fragments
    ├── Services (app/services/)
    │   ├── calendar_service.py      → ICS fetching, event caching, alarm extraction
    │   ├── image_service.py         → GalleryManager for uploads/resizing
    │   └── weather_service.py       → Open-Meteo integration
    ├── Database (app/db/)
    │   ├── models.py         → SQLModel entities (Preset, Photo, CalendarSource, etc.)
    │   ├── engine.py         → SQLAlchemy engine setup
    │   └── session.py        → FastAPI dependency for DB sessions
    ├── Templates (app/templates/)
    │   ├── index.html        → Modern SPA
    │   ├── admin_base.html   → Admin shell with sidebar
    │   ├── admin.html        → Admin main view
    │   ├── legacy/index.html → iPad 2 legacy UI
    │   └── partials/         → HTMX fragment responses
    └── Static Assets (app/static/)
        ├── js/htmx.min.js    → HTMX library (vendored)
        ├── manifest.json     → PWA metadata
        ├── sw.js             → Service worker
        └── css/              → Custom styles
```

## Identified Patterns

### 1. Service Layer for Business Logic

**Location:** `app/services/`
**Purpose:** Encapsulate complex operations (calendar sync, image processing, weather)
**Implementation:** Static methods in service classes called from routers
**Example:** `CalendarService.sync_calendar_events()` → fetches ICS, parses events, extracts alarms, caches results

### 2. Layered Request Handling (Router → Service → Database)

**Location:** Routers call Services; Services call Database models via SQLModel
**Flow:**

```
HTTP Request
    ↓
Router (validate, extract params)
    ↓
Service (business logic, external APIs)
    ↓
Database layer (SQLModel queries)
    ↓
HTTP Response (JSON or TemplateResponse)
```

### 3. HTMX-Driven Admin UI

**Location:** `app/routers/admin.py` and `app/templates/partials/`
**Purpose:** Dynamic admin interface without full page reloads
**Pattern:** Router endpoints return HTML fragments wrapped in TemplateResponse; client-side HTMX swaps content
**Example:**

- User submits settings form → POST /admin/settings
- Server updates database → returns HX-Redirect to /admin/partials/settings
- HTMX refreshes settings panel client-side

### 4. Dual Slideshow UIs (Modern + Legacy)

**Location:** `app/routers/dashboard.py`
**Pattern:**

- **Modern:** `/` serves modern SPA (CSS Grid, ES6 JavaScript)
- **Legacy:** `/legacy` serves iPad 2-compatible UI (ES5, basic CSS)
- Auto-detection: User-Agent parsing detects iPad 2 (iOS 9) → auto-redirect
- **Component fragments:** `/components/slide`, `/components/weather` return HTML for dynamic updates

### 5. Background Job Scheduling

**Location:** `app/main.py` (lifespan context manager) + APScheduler
**Pattern:** Jobs registered at startup, run asynchronously in background
**Example:** Calendar sync every 10 minutes

```python
scheduler.add_job(
    background_sync_calendars,
    "interval",
    minutes=10,
)
```

### 6. Database Dependency Injection

**Location:** `app/db/session.py` + FastAPI Depends
**Pattern:** Get DB session via dependency injection in route handlers
**Example:**

```python
@router.get("/")
async def read_root(session: Session = Depends(get_session)):
    # session is automatically provided
```

## Data Flow

### Calendar Sync Flow

```
APScheduler (every 10 min)
    ↓
CalendarService.sync_calendar_events()
    ├─ Fetch all CalendarSource URLs via httpx (with backoff retry)
    ├─ Parse ICS content (icalevents library)
    ├─ Extract events & VALARM entries (time-based + non-time alarms)
    ├─ Cache events in CalendarEventCache (1-week window)
    ├─ Create AlarmEvent rows for upcoming alarms
    └─ Update CalendarSyncStatusEntry (status, timestamps, error tracking)
```

### Photo Slideshow Flow

```
Client Request: GET /components/slide
    ↓
Router: get_next_slide()
    ├─ Query AppSettings → get active_preset_id
    ├─ Query Photo records for preset
    ├─ Randomly select or cycle through images
    ├─ Return HTML fragment with <img src="/media/image/{id}">
    └─ Client renders in modern/legacy UI
```

### Image Upload & Display Flow

```
Admin: POST /admin/upload (HTMX)
    ↓
Router: upload_file() calls GalleryManager.save_upload()
    ├─ Validate file (JPEG/PNG/HEIF)
    ├─ Resize to multiple resolutions (thumbnail, display, full)
    ├─ Determine preset folder (from form) or create default
    ├─ Save files to data/uploads/{preset_name}/
    ├─ Create Photo record in database
    └─ Return fragment HTML (updated gallery preview)
        ↓
Client: HTMX swaps gallery panel
```

### Weather Display Flow

```
Component: GET /components/weather
    ↓
Router: get_weather()
    ├─ Query AppSettings (weather_latitude, weather_longitude)
    ├─ Call WeatherService.get_current_weather(lat, lon)
    │   ├─ Query Open-Meteo API (no auth required)
    │   └─ Extract temperature, weather code
    ├─ Return minimal HTML fragment
    └─ Client renders in slideshow
```

## Code Organization

**Approach:** Feature-based layers (routers organize by feature; services encapsulate logic)

**Module Boundaries:**

- **Routers:** HTTP request/response handling, parameter validation, template rendering
- **Services:** Business logic, external API calls, data transformation
- **Models:** Data structure definition (SQLModel), relationships
- **Database:** Engine setup, session dependency

## Architecture Decisions

1. **SQLModel (not raw SQLAlchemy):** Combines Pydantic validation with SQLAlchemy ORM for data consistency
2. **Async-first:** FastAPI routes are async; services support async calls (httpx, APScheduler AsyncIOScheduler)
3. **Service layer isolation:** External dependencies (weather, geocoding, calendar) abstracted via services
4. **In-memory SQLite for tests:** Fast, isolated test execution
5. **No auth layer yet:** Admin accessed via direct routes; could add server-side session management later
6. **HTMX over API:** Admin UI uses HTML fragments, reducing JavaScript complexity

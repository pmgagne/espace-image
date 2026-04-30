# Project Structure

**Root:** `/Users/philippegagne/Documents/Projets/espace-image`

## Directory Tree

```
espace-image/
├── app/                          # Main application package
│   ├── main.py                   # FastAPI app setup, APScheduler, lifespan
│   ├── core/                     # Core utilities (currently minimal)
│   ├── db/                       # Database layer
│   │   ├── engine.py             # SQLAlchemy engine, DB initialization
│   │   ├── models.py             # SQLModel entities (Preset, Photo, Calendar, etc.)
│   │   ├── session.py            # FastAPI dependency for DB session
│   │   └── __init__.py
│   ├── routers/                  # HTTP endpoints organized by feature
│   │   ├── dashboard.py          # Slideshow views (/ and /legacy)
│   │   ├── media.py              # Photo/image endpoints
│   │   ├── admin.py              # Admin UI with HTMX fragments
│   │   └── __init__.py
│   ├── services/                 # Business logic & external integrations
│   │   ├── calendar_service.py   # ICS fetching, event parsing, alarm extraction
│   │   ├── image_service.py      # GalleryManager for uploads, resizing
│   │   ├── weather_service.py    # Open-Meteo integration
│   │   └── __init__.py
│   ├── static/                   # Frontend assets
│   │   ├── js/
│   │   │   └── htmx.min.js       # HTMX library (vendored)
│   │   ├── css/
│   │   │   └── admin-forms.css   # Admin styling
│   │   ├── polyfills/            # Legacy polyfills for iPad 2
│   │   │   ├── fetch.umd.js
│   │   │   └── promise.min.js
│   │   ├── manifest.json         # PWA manifest (modern UI)
│   │   ├── admin-manifest.json   # PWA manifest (admin)
│   │   ├── legacy-manifest.json  # PWA manifest (legacy iPad 2)
│   │   ├── sw.js                 # Service worker
│   │   └── [others]
│   └── templates/                # Server-side Jinja2 templates
│       ├── index.html            # Modern slideshow SPA
│       ├── admin_base.html       # Admin shell (sidebar + content area)
│       ├── admin.html            # Admin main view
│       ├── base.html             # Base template for inheritance
│       ├── legacy/
│       │   └── index.html        # iPad 2 legacy UI (ES5 compatible)
│       └── partials/             # HTMX fragment responses
│           ├── calendars.html
│           ├── debug.html
│           ├── gallery.html
│           ├── settings.html
│           └── [others]
│
├── data/                         # Runtime data (uploads, database)
│   ├── uploads/                  # User-uploaded photos organized by preset
│   │   ├── Default/
│   │   ├── Normal/
│   │   ├── Noël/
│   │   ├── test/
│   │   └── [preset names]/
│   └── espace_image.db           # SQLite database (created at runtime)
│
├── tests/                        # Test suite
│   ├── conftest.py               # pytest config, fixtures (session, client)
│   ├── test_app.py               # Core app tests
│   ├── test_routers.py           # Endpoint tests
│   ├── test_calendar_service.py  # Calendar sync & parsing
│   ├── test_calendar_integration.py
│   ├── test_image_service.py     # Image upload & processing
│   ├── test_admin_search.py      # Geocoding search
│   ├── test_debug_panel.py
│   ├── test_multi_alarm.py       # Multi-alarm handling
│   ├── test_non_time_alarm.py    # Non-time-based alerts
│   ├── images/                   # Test images
│   └── __pycache__/
│
├── alembic/                      # Database migrations (Alembic setup)
│   └── versions/
│
├── scripts/                      # Utility scripts
│   ├── generate_icons.py         # PWA icon generation (uses CairoSVG)
│   └── write_simple_pngs.py      # PNG test file generation
│
├── docs/                         # Documentation
│   ├── db/
│   │   └── DB.md                 # Database schema docs
│   └── webcal/
│       ├── rfc5545.txt           # ICS format reference
│       └── rfc9074.txt           # RFC for calendar handling
│
├── Dockerfile                    # Containerization
├── docker-compose.yml            # Compose for local dev/testing
├── pyproject.toml                # Project metadata, dependencies, tool config
├── init_db.py                    # Database initialization helper
├── README.md                     # Project overview
├── CONTRIBUTING.md               # Contribution guidelines
├── LICENSE                       # License
└── PWA-INSTALL.md                # PWA installation instructions
```

## Module Organization

### Routers (Request Handling)

**Purpose:** Map HTTP endpoints to handler functions
**Location:** `app/routers/`

| File | Route Prefix | Features | Purpose |
|------|--------------|----------|---------|
| `dashboard.py` | None | `/`, `/legacy`, `/components/*` | Slideshow views (modern & iPad 2 legacy) |
| `media.py` | `/media` | `/media/image/{id}`, `/media/thumbnail/{id}` | Photo retrieval & resizing |
| `admin.py` | `/admin` | `/admin/`, `/admin/partials/*`, `/admin/upload` | Admin UI, settings, photo management |

### Services (Business Logic)

**Purpose:** Encapsulate domain operations
**Location:** `app/services/`

| File | Class | Key Methods | Purpose |
|------|-------|------------|---------|
| `calendar_service.py` | `CalendarService` | `sync_calendar_events()`, `parse_ics()`, `extract_alarms()` | Calendar ICS fetching, event caching, alarm detection |
| `image_service.py` | `GalleryManager` | `save_upload()`, `get_resized_image()` | Photo upload validation, resizing to multiple resolutions |
| `weather_service.py` | `WeatherService` | `get_current_weather()` | Open-Meteo API queries |

### Database (Data Access)

**Purpose:** ORM models and session management
**Location:** `app/db/`

| File | Contents | Purpose |
|------|----------|---------|
| `models.py` | SQLModel entities: `Preset`, `Photo`, `CalendarSource`, `AppSettings`, `AlarmEvent`, `CalendarEventCache`, `CalendarSyncStatusEntry` | Data structure definitions |
| `engine.py` | SQLAlchemy engine, `create_db_and_tables()` | Database connection & initialization |
| `session.py` | `get_session()` (FastAPI dependency) | DB session injection in routes |

### Templates (Rendering)

**Purpose:** Server-side HTML rendering
**Location:** `app/templates/`

| File/Folder | Context | Purpose |
|-------------|---------|---------|
| `index.html` | Modern slideshow | ES6 JavaScript, CSS Grid, dynamic image updates |
| `legacy/index.html` | iPad 2 slideshow | ES5 polyfills, fixed layout, compatible with iOS 9 |
| `admin_base.html` | Admin shell | Sidebar + content area structure |
| `admin.html` | Admin main | Dashboard view |
| `base.html` | Shared | Template inheritance base |
| `partials/*` | HTMX responses | Auto-inserted HTML fragments for admin UI |

## Where Things Live

### Photo Slideshow

- **UI/Interface:** `app/templates/index.html` (modern), `app/templates/legacy/index.html` (iPad 2)
- **Business Logic:** `app/routers/dashboard.py::get_next_slide()`, `app/services/image_service.py::get_resized_image()`
- **Data Access:** `app/db/models.py::Photo`, `app/db/models.py::Preset`

### Calendar Management

- **UI/Interface:** `app/templates/partials/calendars.html`, `app/templates/partials/settings.html`
- **Business Logic:** `app/services/calendar_service.py` (ICS parsing, event extraction)
- **Background Sync:** `app/main.py::background_sync_calendars()` (APScheduler every 10 min)
- **Data Access:** `app/db/models.py::CalendarSource`, `CalendarEventCache`, `AlarmEvent`

### Admin Panel

- **UI/Interface:** `app/templates/admin_base.html`, `app/templates/admin.html`, `app/templates/partials/*`
- **Business Logic:** `app/routers/admin.py` (all endpoints)
- **Interactions:** HTMX fragments, form submissions with HX-Redirect
- **Data Access:** All models (settings, uploads, calendars, alarms)

### Weather Display

- **UI/Interface:** HTML fragment in `app/routers/dashboard.py::get_weather()`
- **Business Logic:** `app/services/weather_service.py::get_current_weather()`
- **Data Access:** `app/db/models.py::AppSettings` (coordinates)

### Photo Upload & Resizing

- **UI/Interface:** `app/templates/partials/gallery.html`
- **Business Logic:** `app/routers/admin.py::upload_file()`, `app/services/image_service.py::save_upload()`
- **Data Access:** `app/db/models.py::Photo`, `Preset`
- **Storage:** `data/uploads/{preset_name}/` with subdirs for resolutions

## Special Directories

| Directory | Purpose | Key Contents |
|-----------|---------|--------------|
| `data/uploads/` | User photo storage | Organized by preset; contains resized images (thumbnail, display, full) |
| `data/` | Runtime data | SQLite database, uploads |
| `alembic/` | Database migrations | Alembic setup (not actively used; schema managed via SQLModel tables) |
| `scripts/` | Utility scripts | Icon generation (CairoSVG), test data generation |
| `docs/` | Reference documentation | DB schema, RFC standards for calendar handling |
| `app/static/polyfills/` | Compatibility shims | Promise & Fetch polyfills for iPad 2 (ES5) |

## Key Files at Root

| File | Purpose |
|------|---------|
| `init_db.py` | Helper script to initialize database |
| `pyproject.toml` | Project metadata, dependencies, tool configuration |
| `Dockerfile` | Container image definition |
| `docker-compose.yml` | Local dev/test container orchestration |
| `README.md` | Project overview, quick start |

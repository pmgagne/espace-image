# Tech Stack

**Analyzed:** February 10, 2026

## Core

- **Framework:** FastAPI 0.123.10+ (Python web framework with async support)
- **Language:** Python 3.13+
- **Runtime:** uvicorn 0.40.0 (ASGI server)
- **Package Manager:** uv (fast Python package manager)

## Backend/API

- **API Style:** REST (JSON + HTML fragments via HTMX)
- **Database ORM:** SQLModel 0.0.31 (combining Pydantic + SQLAlchemy)
- **Database:** SQLite (default, configurable via DATABASE_URL)
- **Templating:** Jinja2 3.1.6 (server-side rendering)
- **Job Scheduling:** APScheduler 3.11.2+ (async background jobs, 10-min calendar sync intervals)

## Frontend

- **UI Approach:** Modern SPA with HTML fragments + HTMX interaction
- **Legacy UI:** ES5-compatible (iPad 2 support, iOS 9.3.5)
- **CSS:** Custom CSS (no framework; legacy uses basic layouts, modern uses CSS Grid)
- **Styling Approach:** Inline CSS files in app/static/css/
- **Interactivity:** HTMX 1.9+ (vendored in app/static/js/htmx.min.js)

## Image Handling

- **Image Processing:** Pillow 11.3.0 (PIL Fork)
- **HEIF Support:** pillow-heif 1.2.0 (modern image format support)
- **Icon Generation:** CairoSVG 2.8.2 (dev-only, for PWA icon generation)

## External Service Integration

- **HTTP Client:** httpx 0.28.1 (async HTTP with timeouts)
- **Calendar Data:** icalendar 6.1.0 (ICS parsing)
- **Timezone Support:** pytz 2025.2, dateutil (via icalendar)
- **Retry Logic:** backoff 2.2.1 (exponential backoff for resilient API calls)
- **Weather API:** Open-Meteo (free, no auth required)
- **Geocoding:** Nominatim/OpenStreetMap (reverse geocoding for location names)

## File Upload

- **Multipart Handling:** python-multipart 0.0.21 (FastAPI file uploads)
- **Upload Storage:** File-based (data/uploads/ organized by preset folders)

## Testing

- **Framework:** pytest 9.0.2
- **Coverage:** pytest-cov 6.0.0 (with coverage tracking)
- **Test Database:** SQLite in-memory (isolated per test)
- **Test Client:** FastAPI TestClient (local testing without HTTP)

## Development Tools

- **Linting/Formatting:** Ruff 0.14.11 (Python linter + formatter)
- **Type Checking:** Pyright (strict mode for Python 3.13)
- **Logging:** Python standard library (configurable via LOG_LEVEL env var)

## Production Deployment

- **Containerization:** Docker + Docker Compose (Dockerfile + docker-compose.yml)
- **Static Files:** FastAPI static file mounting under /static

## Key Dependencies Summary

| Category | Library | Version | Purpose |
|----------|---------|---------|---------|
| Core Framework | FastAPI | 0.123.10 | Web framework |
| Server | uvicorn | 0.40.0 | ASGI server |
| Database | SQLModel | 0.0.31 | ORM + data validation |
| Scheduling | APScheduler | 3.11.2 | Background job scheduling |
| Image Processing | Pillow | 11.3.0 | Image resizing/manipulation |
| HTTP | httpx | 0.28.1 | Async HTTP client |
| Calendar | icalendar | 6.1.0 | ICS parsing |
| Retry Logic | backoff | 2.2.1 | Exponential backoff |
| Testing | pytest | 9.0.2 | Test framework |
| Linting | Ruff | 0.14.11 | Code formatting/linting |

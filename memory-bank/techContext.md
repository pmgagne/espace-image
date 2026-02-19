# Tech Context — Espace-Image

**Based on**: `pyproject.toml`, `.specs/codebase/STACK.md`

## Technology Stack

### Core Runtime

- **Language**: Python 3.13+
- **Framework**: FastAPI 0.123.10+ (async web framework)
- **Server**: uvicorn 0.40.0 (ASGI server with hot reload)
- **Package Manager**: [uv](https://docs.astral.sh/uv/) (fast Python dependency management)

### Backend Stack

- **Database**: SQLite (single-file, no external server)
- **ORM**: SQLModel 0.0.31 (Pydantic + SQLAlchemy)
- **Templating**: Jinja2 3.1.6 (server-side HTML rendering)
- **Background Jobs**: APScheduler 3.11.2 (AsyncIOScheduler for 10-min calendar sync)
- **HTTP Client**: httpx 0.28.1 (async HTTP with timeout support)
- **Retry Logic**: backoff 2.2.1 (exponential backoff for external APIs)

### Frontend Stack

- **UI Pattern**: HTMX 1.9+ (HTML fragments, no client-side state)
- **Styling**: Custom CSS (no framework, utility classes in `admin-forms.css`)
- **Modern JavaScript**: ES6+ (async/await, modules, IIFE pattern)
- **Legacy JavaScript**: ES5 (iPad 2 compatibility, no arrow functions/template literals)
- **Progressive Enhancement**: Works without JavaScript for static slideshow

### Calendar & Time Handling

- **Calendar Parsing**: icalevents 0.1.29 (ICS parsing + recurrence expansion)
- **Timezone**: pytz 2025.2 (IANA timezone database)
- **Date Utilities**: python-dateutil (via dependencies)
- **Time Storage**: UTC with `datetime.now(UTC)` or `timezone.utc`

### Image Processing

- **Main Library**: Pillow 11.3.0 (PIL fork for resize, optimization, format conversion)
- **HEIC Support**: pillow-heif 1.2.0 (HEIF/HEIC format support for iPhone photos)
- **Optimization**: JPEG quality 85, progressive encoding, max 1920px dimension
- **Icon Generation**: CairoSVG 2.8.2 (dev-only, SVG → PNG for PWA icons)

### External Service Integration

- **Weather API**: [Open-Meteo](https://open-meteo.com/) (free, no auth, no API key)
- **Geocoding**: [Nominatim](https://nominatim.org/) (OpenStreetMap reverse geocoding)
- **Rate Limiting**: In-memory (6 req/min for Weather, 3 req/min for Geocoding)

### File Upload

- **Multipart Handling**: python-multipart 0.0.21 (FastAPI file upload support)
- **Allowed Extensions**: `.jpg`, `.jpeg`, `.png`, `.heic`, `.heif`
- **Validation**: Extension check + PIL magic byte verification
- **Storage**: File-based in `data/uploads/{preset_name}/`

### Testing

- **Framework**: pytest 9.0.2
- **Coverage**: pytest-cov 6.0.0 (HTML + XML coverage reports)
- **Test Client**: FastAPI TestClient (simulated HTTP requests, no network)
- **Database**: SQLite in-memory (`:memory:`, isolated per test)
- **Fixtures**: pytest fixtures for session, client, sample data

### Development Tools

- **Linter**: Ruff 0.14.11 (Python linting + auto-formatting)
- **Type Checker**: Pyright (strict mode, Python 3.13)
- **Logging**: Python `logging` module (configured via `LOG_LEVEL` env var)
- **Frontend Linting**: htmlhint, stylelint, eslint (via npm scripts)

### Production Deployment

- **Containerization**: Docker + Docker Compose
- **Base Image**: python:3.13-slim
- **Static Files**: FastAPI `StaticFiles` mounted at `/static`
- **Volume Mounts**: `./data:/app/data` for uploads and database
- **Port**: 8000 (HTTP, no HTTPS in container — use reverse proxy)

## Development Setup

### Prerequisites

1. Python 3.13+ installed
2. [uv](https://docs.astral.sh/uv/) package manager
3. Node.js (for frontend linting only)
4. Git

### Local Development Workflow

```bash
# 1. Clone repository
git clone https://github.com/pmgagne/espace-image.git
cd espace-image

# 2. Install Python dependencies
uv sync --dev

# 3. Run development server
uv run uvicorn app.main:app --reload

# 4. Run tests
uv run pytest tests/ -v --cov=app

# 5. Lint Python code
uv run ruff check .
uv run ruff format . --check

# 6. Lint frontend code (HTML/CSS/JS)
npm install  # One-time
npm run lint
```

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `LOG_LEVEL` | `INFO` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `DATABASE_URL` | `sqlite:///data/app.db` | SQLite database file path |
| `WEBAPP_DEBUG` | _unset_ | Enable debug endpoints when `true` |

### Docker Development

```bash
# Build image
docker build -t espace-image:latest .

# Run with volume mounts
docker run -d \
  --name espace-image \
  -p 8000:8000 \
  -v ./data:/app/data \
  -e LOG_LEVEL=DEBUG \
  --restart unless-stopped \
  espace-image:latest

# View logs
docker logs -f espace-image
```

## Technical Constraints

### Browser Compatibility

- **Modern**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Legacy**: Safari on iOS 9.3.5 (WebKit 600.1.4)
- **ES5 Required**: No arrow functions, template literals, or destructuring in `legacy.js`
- **CSS Limitations**: No CSS Grid, Flexbox only in legacy mode

### Performance Requirements

- **Image Size**: < 1MB per optimized image (iPad 2 memory constraint)
- **Page Load**: < 2 seconds on iPad 2 over WiFi
- **Calendar Sync**: < 5 seconds per ICS feed (10-minute intervals)
- **Memory Usage**: < 200MB RSS (background worker + web server)

### Security Constraints

- **No Authentication**: Internal network deployment only (documented in `SECURITY.md`)
- **SSRF Protection**: URL scheme validation (`http`/`https`/`webcal` only)
- **XSS Protection**: HTML escaping mandatory (Jinja2 auto-escape + manual `markupsafe.escape()`)
- **Path Traversal**: Canonical path validation with `Path.resolve().is_relative_to()`

### API Rate Limits

- **Open-Meteo**: 10,000 requests/day (free tier), 6 req/min rate limited
- **Nominatim**: 1 request/second max, 3 req/min rate limited
- **Calendar Feeds**: 10-minute sync interval (144 requests/day per feed)

## Dependencies

### Production Dependencies

(From `pyproject.toml`)

```toml
dependencies = [
    "apscheduler>=3.11.2",
    "backoff>=2.2.1",
    "fastapi>=0.123.10",
    "httpx>=0.28.1",
    "icalevents>=0.1.29",
    "jinja2>=3.1.6",
    "pillow>=11.3.0",
    "pillow-heif>=1.2.0",
    "python-multipart>=0.0.21",
    "pytz>=2025.2",
    "sqlmodel>=0.0.31",
    "uvicorn>=0.40.0",
]
```

### Development Dependencies

```toml
dev = [
    "cairosvg>=2.8.2",    # PWA icon generation
    "pytest>=9.0.2",
    "pytest-cov>=6.0.0",
    "ruff>=0.14.11",
]
```

## CI/CD Pipeline

### GitHub Actions Workflows

**On Push/PR**:
- Python linting (ruff check + format)
- Frontend linting (HTML/CSS/JS validation)
- Unit tests with coverage reporting
- Security scanning (Trivy)
- Docker build validation

**Manual Triggers**:
- Docker image publish to registry
- Documentation deployment

### Quality Gates

All checks must pass before merge to `main`:
- ✓ Ruff linting (no errors)
- ✓ All tests passing (68 tests)
- ✓ No security vulnerabilities (Trivy)
- ✓ Docker image builds successfully

## Related Documents

- [.specs/codebase/STACK.md](../.specs/codebase/STACK.md) — Detailed stack reference
- [systemPatterns.md](systemPatterns.md) — Architecture and design patterns
- [.specs/codebase/TESTING.md](../.specs/codebase/TESTING.md) — Test strategy
- [CONTRIBUTING.md](../CONTRIBUTING.md) — Development workflow

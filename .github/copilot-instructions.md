# GitHub Copilot Instructions for Espace Image Dashboard

## Project Overview

**Espace Image** is a FastAPI-based dashboard application that serves modern and legacy UIs (optimized for iPad 2 / iOS 9.3.5). It features photo slideshows, calendar alarms (iCloud Calendar integration), weather widgets, and HTMX-powered admin interactions.

**Tech Stack:**
- **Backend:** FastAPI 0.123+, Python 3.13+
- **Database:** SQLModel (SQLite for development)
- **Frontend:** HTMX 1.0 (ES5 for legacy), Jinja2 templates, vanilla CSS
- **Package Manager:** `uv` (not pip/poetry)
- **Testing:** pytest, pytest-cov
- **Linting/Formatting:** Ruff
- **Deployment:** Docker, Docker Compose

---

## Development Setup & Commands

### Package Management (ALWAYS use `uv`)
```bash
# Install dependencies (first time or after changes to pyproject.toml)
uv sync --dev

# Add a new dependency
uv add <package-name>

# Add a dev dependency
uv add --dev <package-name>

# Run commands in the uv-managed venv
uv run <command>

# DO NOT use pip install, poetry, or manual venv creation
```

### Running the Application
```bash
# Development server with auto-reload
uv run uvicorn app.main:app --reload

# Production-like (no reload)
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Run all tests with coverage
uv run pytest tests/ -v --cov=app --cov-report=xml

# Run specific test file
uv run pytest tests/test_admin_search.py -v

# Run tests matching a pattern
uv run pytest -k "calendar" -v
```

### Linting & Formatting
```bash
# Check code style
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Check code formatting
uv run ruff format --check .

# Auto-format code
uv run ruff format .
```

### Docker
```bash
# Build and run with Docker Compose
docker-compose up --build

# Build image manually
docker build -t espace-image:latest .

# Run container
docker run -d -p 8000:8000 -v ./data:/app/data espace-image:latest
```

---

## Code Style & Best Practices

### Python Code
- **Python Version:** 3.13+ (use modern syntax: match/case, type hints, f-strings)
- **Line Length:** 100 characters (ruff config)
- **Imports:** Auto-sorted by Ruff (isort rules)
- **Type Hints:** ALWAYS use type hints for function signatures
- **Async:** Prefer `async def` for route handlers in FastAPI

**Example:**
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db.session import get_session
from app.db.models import Photo, Preset

router = APIRouter()

@router.get("/photos/{photo_id}")
async def get_photo(
    photo_id: int,
    session: Session = Depends(get_session)
) -> Photo:
    """Fetch a single photo by ID."""
    photo = session.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    return photo
```

### Template & Frontend Code
- **Templates:** Jinja2 (in `app/templates/`)
- **Static Files:** `app/static/` (js, css, manifest.json)
- **HTMX:** Use `hx-get`, `hx-post`, `hx-target`, `hx-swap` attributes for dynamic content
- **Legacy Support:** `app/templates/legacy/` uses ES5 JS (no arrow functions, const/let, template literals)
- **CSS (Modern):** Use modern CSS features (Grid, CSS variables, flexbox). Use utility classes from `app/static/css/main.css` when available; avoid excessive inline styles.
- **CSS (Legacy):** Emulate the modern UI's aesthetic while adhering to legacy constraints. Tune specifically for iPad 2 landscape (1024x768) and portrait (768x1024) displays.

**HTMX Example:**
```html
<button hx-post="/admin/upload"
        hx-target="#admin-content"
        hx-encoding="multipart/form-data">
    Upload Photos
</button>
```

**Legacy JS (iPad 2 / iOS 9 compatible):**
```javascript
// Good (ES5)
var btn = document.getElementById('my-btn');
btn.addEventListener('click', function() {
    console.log('clicked');
});

// Bad (ES6+) - breaks on iPad 2
const btn = document.getElementById('my-btn');
btn.addEventListener('click', () => console.log('clicked'));
```

### Database Models (SQLModel)
- **Location:** `app/db/models.py`
- **Engine Setup:** `app/db/engine.py`
- **Session Management:** `app/db/session.py` (use `get_session` dependency)
- **Migrations:** Currently manual (create_db_and_tables on startup)

**Example Model:**
```python
from sqlmodel import Field, SQLModel, Relationship

class Preset(SQLModel, table=True):
    __tablename__ = "presets"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)

    # Relationships
    photos: list["Photo"] = Relationship(back_populates="preset")
```

---

## Project Structure

```
app/
├── main.py              # FastAPI app entry point, router includes
├── core/                # Core configuration (future: settings, logging)
├── db/
│   ├── engine.py        # Database engine and table creation
│   ├── models.py        # SQLModel table definitions
│   └── session.py       # Session dependency injection
├── routers/
│   ├── admin.py         # Admin panel routes (/admin/*)
│   ├── dashboard.py     # Main dashboard routes (/, /legacy)
│   └── media.py         # Image serving routes (/images/*)
├── services/
│   ├── calendar_service.py  # iCloud Calendar integration
│   ├── image_service.py     # Image upload/processing
│   └── weather_service.py   # Open-Meteo API integration
├── static/
│   ├── css/
│   │   └── main.css     # Global styles (form controls, buttons, utilities)
│   ├── js/
│   │   ├── htmx.min.js  # HTMX 1.0 (ES5 build)
│   │   └── file-input.js # File upload UI helpers
│   ├── polyfills/       # Promise & Fetch polyfills for iOS 9
│   └── manifest.json    # PWA manifest
└── templates/
    ├── base.html            # Base template (modern pages)
    ├── admin_base.html      # Admin panel base
    ├── index.html           # Main dashboard (modern)
    ├── admin.html           # Admin panel (fallback non-HTMX)
    ├── legacy/
    │   └── index.html       # Legacy dashboard (iPad 2 optimized)
    └── partials/
        ├── calendars.html   # Calendar management partial (HTMX)
        ├── gallery.html     # Gallery management partial (HTMX)
        └── settings.html    # Settings partial (HTMX)

tests/                   # pytest test suite
data/                    # SQLite database and uploaded images (gitignored)
```

---

## API & Framework References

### FastAPI
- **Docs:** https://fastapi.tiangolo.com/
- **Key Concepts:** Dependency injection, async routes, Pydantic models, `HTTPException`
- **Routing:** Use `APIRouter` in `app/routers/`, include in `app/main.py`

### SQLModel
- **Docs:** https://sqlmodel.tiangolo.com/
- **Key Concepts:** Combines SQLAlchemy + Pydantic; use `Session` for queries, `select()` for type-safe queries
- **Relationships:** Define with `Relationship()` and back_populates

### HTMX
- **Docs:** https://htmx.org/docs/
- **Version:** 1.0 (ES5 build for legacy browser support)
- **Key Attributes:** `hx-get`, `hx-post`, `hx-delete`, `hx-target`, `hx-swap`, `hx-trigger`, `hx-encoding`
- **Events:** Use `htmx:afterSwap`, `htmx:afterOnLoad` for JS hooks

### Jinja2
- **Docs:** https://jinja.palletsprojects.com/
- **Key Concepts:** `{% block %}`, `{% extends %}`, `{{ variable }}`, `{% if %}`, `{% for %}`
- **Filters:** Use built-in filters like `|length`, `|default`, `|safe`

### uv
- **Docs:** https://docs.astral.sh/uv/
- **Key Commands:** `uv sync`, `uv add`, `uv run`, `uv pip compile`
- **NEVER use:** `pip install`, `poetry add`, manual venv activation

---

## Testing Guidelines

### Test Structure
- **Location:** `tests/` directory
- **Naming:** `test_*.py` files, `test_*` functions
- **Fixtures:** Use `conftest.py` for shared fixtures
- **Coverage Target:** Maintain >80% coverage

### Writing Tests
```python
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.models import Preset

client = TestClient(app)

def test_get_presets(test_session):
    """Test listing presets."""
    # Arrange
    preset = Preset(name="Test Preset")
    test_session.add(preset)
    test_session.commit()

    # Act
    response = client.get("/admin/presets")

    # Assert
    assert response.status_code == 200
    assert "Test Preset" in response.text
```

### Running Tests
```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ -v --cov=app --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_calendar_service.py -v

# Run tests matching pattern
uv run pytest -k "upload" -v
```

---

## Common Patterns & Solutions

### Adding a New Admin Route
1. Define route in `app/routers/admin.py`
2. Use `Depends(get_session)` for DB access
3. Return `TemplateResponse` or use `hx-get`/`hx-post` for HTMX partials
4. Add partial template to `app/templates/partials/` if needed

### Adding a New Database Model
1. Define in `app/db/models.py` using SQLModel
2. Ensure `create_db_and_tables()` is called on startup (already in `app/main.py`)
3. Use `Session` dependency in routes to query

### Styling Form Controls
- Use `.form-control` class for inputs, selects
- Use `.btn` class for buttons
- Use `.file-wrapper` + `.file-label` pattern for file inputs
- Use `.panel` class for card-like containers
- Reference `app/static/css/main.css` for available utilities

### Handling File Uploads
```python
from fastapi import UploadFile, File

@router.post("/upload")
async def upload_photos(
    files: list[UploadFile] = File(...),
    session: Session = Depends(get_session)
):
    for file in files:
        content = await file.read()
        # Process file...
    return {"uploaded": len(files)}
```

### HTMX Response Pattern
```python
@router.get("/admin/partials/settings")
async def get_settings_partial(
    request: Request,
    session: Session = Depends(get_session)
):
    settings = session.exec(select(Settings)).first()
    return templates.TemplateResponse(
        "partials/settings.html",
        {"request": request, "settings": settings}
    )
```

---

## Legacy Browser Support (iPad 2 / iOS 9)

### JavaScript Constraints
- **No ES6+:** No arrow functions, const/let, template literals, async/await
- **Polyfills Required:** Promise, Fetch (included in `app/static/polyfills/`)
- **Use ES5 syntax:**
  ```javascript
  // Good
  var items = [1, 2, 3];
  items.forEach(function(item) { console.log(item); });

  // Bad
  const items = [1, 2, 3];
  items.forEach(item => console.log(item));
  ```

### CSS Constraints
- **No CSS Grid:** Use flexbox or floats
- **No backdrop-filter:** Use solid rgba backgrounds
- **Vendor prefixes:** Use `-webkit-` for transforms, transitions, flexbox

### HTMX on Legacy
- HTMX 1.0 ES5 build is used (`app/static/js/htmx.min.js`)
- Legacy page (`app/templates/legacy/index.html`) uses manual XHR instead of HTMX for some interactions

---

## DO's and DON'Ts

### DO
✅ Use `uv` for all package management
✅ Write async route handlers in FastAPI
✅ Add type hints to all function signatures
✅ Use HTMX for dynamic admin UI updates
✅ Test your code with `pytest` before committing
✅ Run `ruff check` and `ruff format` before pushing
✅ Use SQLModel `Session` with dependency injection
✅ Follow existing patterns in `app/routers/` and `app/services/`
✅ Use utility classes from `main.css` for consistent styling

### DON'T
❌ Use `pip install` or `poetry` (use `uv` instead)
❌ Use ES6+ syntax in legacy templates or JS files
❌ Add inline styles excessively (use CSS classes)
❌ Commit without running tests and linting
❌ Hardcode configuration (use environment variables or DB settings)
❌ Use CSS Grid in legacy templates (iPad 2 incompatible)
❌ Ignore type hints or skip docstrings for complex functions
❌ Create migrations manually (SQLModel auto-creates tables on startup)

---

## Environment Variables

```bash
# Database (optional, defaults to SQLite in data/)
DATABASE_URL=sqlite:///./data/app.db

# Uvicorn settings
HOST=0.0.0.0
PORT=8000
```

---

## Deployment Notes

- **CI/CD:** GitHub Actions workflow in `.github/workflows/ci.yml`
- **Docker Registry:** GitHub Container Registry (ghcr.io)
- **Image Tag:** `ghcr.io/pmgagne/espace-image:main`
- **Volumes:** Mount `./data` for persistent storage
- **Health Check:** `GET /health` returns `{"status": "ok"}`

---

## Additional Resources

- **Project README:** See `/README.md` for quick start and Docker usage
- **Workflow Guide:** See `/.github/WORKFLOW_GUIDE.md` for CI/CD pipeline details
- **uv Documentation:** https://docs.astral.sh/uv/
- **FastAPI Documentation:** https://fastapi.tiangolo.com/
- **HTMX Documentation:** https://htmx.org/
- **SQLModel Documentation:** https://sqlmodel.tiangolo.com/

---

## Summary for AI Agents

When working on this project:
1. **ALWAYS use `uv`** for dependency management and command execution
2. **Follow FastAPI + SQLModel patterns** for backend code
3. **Use HTMX** for admin UI interactions (avoid full page reloads)
4. **Support legacy browsers** (iPad 2 / iOS 9) with ES5 JS and fallback CSS
5. **Write tests** for new features and maintain coverage
6. **Run linting** (`ruff check` + `ruff format`) before committing
7. **Use type hints** and docstrings for clarity
8. **Reference existing code** in `app/routers/`, `app/services/`, and `app/templates/` for patterns

This project values simplicity, backwards compatibility, and maintainability. When in doubt, check existing implementations first.

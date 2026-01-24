# Copilot Context & Rules

This file helps GitHub Copilot understand your project's conventions and provide better suggestions.

## Project Structure
- **app/** - FastAPI application code
  - **main.py** - Entry point, route definitions
  - **core/** - Core business logic, config
  - **db/** - Database models, session, engine
  - **routers/** - API endpoint groups (admin, dashboard, media)
  - **services/** - Business services (calendar, weather, image)
  - **templates/** - Jinja2 HTML templates (legacy iPad support)
  - **static/** - CSS, JS, images, local HTMX/polyfills

- **tests/** - Pytest test files
  - test_*.py pattern for discovery
  - conftest.py for fixtures

- **.github/workflows/** - CI/CD GitHub Actions

## Code Conventions

### Python Style
- **Version**: Python 3.13+
- **Formatter**: Ruff (double quotes, 100-char lines)
- **Linter**: Ruff with E, W, F, I, C, B, UP rules
- **Type Hints**: Strict Pylance checking enabled
- **Imports**: Auto-organized by isort (via ruff)

### Framework & Libraries
- **Web Framework**: FastAPI
- **ORM**: SQLModel (SQLAlchemy + Pydantic)
- **Templates**: Jinja2
- **Images**: Pillow
- **HTTP Client**: httpx
- **Testing**: pytest + anyio
- **Package Manager**: uv

### API Design
- RESTful endpoints in `/app/routers/`
- Pydantic models for request/response validation
- Return `JSONResponse` or auto-serialized dicts
- Use dependency injection (`Depends()`)

### Testing
- Unit tests for services and logic
- Integration tests for routers
- Use pytest fixtures from conftest.py
- Mock external services (weather, calendar)
- Test files: `tests/test_*.py`

### Database
- Models in `app/db/models.py` using SQLModel
- Session management in `app/db/session.py`
- Migrations handled via SQLAlchemy

### Legacy Support (iPad 2, iOS 9.3.5)
- **Dashboard Frontend**: Pure ES5 JavaScript (no HTMX/modern syntax)
  - Uses XMLHttpRequest for requests
  - setInterval for polling
  - var, no const/arrow functions
- **Admin Frontend**: HTMX 1.0.0 (last ES5-compatible version)
  - Local `fetch` polyfill required
  - Local `promise` polyfill required
- **CSS**: No CSS Grid (use flexbox/float)
- **Assets**: All JS/CSS hosted locally in `app/static/`

## Copilot Behavior

When suggesting code:
1. Follow Ruff formatting rules automatically
2. Add type hints to function parameters and returns
3. Include docstrings for complex functions
4. Use Pydantic models for data validation
5. Write tests alongside new features
6. Consider legacy device compatibility
7. Use context-aware variable names

### Do's
✅ Suggest efficient, readable code
✅ Include error handling with appropriate HTTP status codes
✅ Use FastAPI's built-in validation
✅ Organize imports (stdlib, third-party, local)
✅ Add logging for debugging
✅ Use async/await for I/O operations

### Don'ts
❌ Don't suggest ES6+ syntax for legacy frontend
❌ Don't use external CDN for JS libraries (use local)
❌ Don't hardcode secrets (use .env)
❌ Don't ignore type hints
❌ Don't skip error handling
❌ Don't import unused modules

## Common Patterns

### FastAPI Endpoint
```python
@router.get("/items/{item_id}")
async def get_item(item_id: int) -> ItemResponse:
    """Retrieve an item by ID."""
    item = await db_service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return ItemResponse.from_orm(item)
```

### Service Layer
```python
class MyService:
    def __init__(self, db_session: Session) -> None:
        self.db = db_session

    async def process_item(self, item_id: int) -> ItemDTO:
        """Process an item."""
        item = self.db.query(Item).filter(Item.id == item_id).first()
        # ...
        return ItemDTO.from_orm(item)
```

### Test File
```python
@pytest.mark.asyncio
async def test_get_item(client):
    """Test GET /items/{id} endpoint."""
    response = client.get("/items/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1
```

## Questions for Copilot

Use Copilot Chat for:
- "How would you implement X?" (design guidance)
- "Fix this error..." (debugging help)
- "Write a test for..." (test generation)
- "Refactor this to..." (code improvement)
- "Explain why..." (learning)

## Files to Ignore in Context

Copilot should avoid suggesting changes to:
- Vendored libraries in `app/static/js/`
- Generated files (requirements.txt, uv.lock)
- Database migrations (auto-generated)
- Build artifacts in `data/` folder

# Testing Infrastructure

## Test Frameworks

| Purpose | Framework | Version | Usage |
|---------|-----------|---------|-------|
| Test Execution | pytest | 9.0.2 | Core test runner |
| Coverage Reporting | pytest-cov | 6.0.0 | Code coverage analysis |
| HTTP Testing | FastAPI TestClient | (built-in) | Local request testing without HTTP layer |

## Test Organization

**Location:** `tests/`

**Naming Pattern:** `test_*.py` (pytest auto-discovery)

**Test Database:** In-memory SQLite (`:memory:`) with `StaticPool` for thread safety

**Fixtures:** Defined in `conftest.py`, shared across all tests

## Test File Structure

| Test File | Focus | Key Tests |
|-----------|-------|-----------|
| `test_app.py` | Core app functionality | Health check, app setup |
| `test_routers.py` | Route endpoints | Dashboard routes, media routes, parameter validation |
| `test_admin_search.py` | Admin geocoding | Location search via Nominatim, coordinate validation |
| `test_image_service.py` | Image processing | Upload validation, resizing, file handling |
| `test_calendar_service.py` | Calendar parsing | ICS parsing, event extraction, error handling |
| `test_calendar_integration.py` | Full calendar sync | End-to-end sync with mock HTTP, database state |
| `test_debug_panel.py` | Debug features | Debug mode flag, conditional rendering |
| `test_multi_alarm.py` | Multi-alarm handling | Multiple alarms per event, trigger time extraction |
| `test_non_time_alarm.py` | Non-time alarms | Non-time-based alarms (e.g., "at event start") |

## Testing Patterns

### Unit Tests

**Approach:** Isolated testing of individual functions/methods

**Location:** Distributed across test files (e.g., `test_image_service.py`, `test_calendar_service.py`)

**Example pattern:**

```python
def test_parse_ics_valid():
    """Test ICS parsing with valid content."""
    ics_content = "BEGIN:VCALENDAR\n..."
    calendar = CalendarService.parse_ics(ics_content)
    assert calendar is not None
    assert len(calendar.walk('VEVENT')) > 0

def test_parse_ics_invalid():
    """Test ICS parsing with invalid content."""
    ics_content = "INVALID"
    calendar = CalendarService.parse_ics(ics_content)
    assert calendar is None
```

**Mocking:** Uses `unittest.mock.patch` for external dependencies

```python
@patch("httpx.AsyncClient.get")
async def test_sync_calendars_with_retry(mock_get):
    """Test calendar sync with HTTP retry logic."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = "BEGIN:VCALENDAR\n..."
    # Execute sync, assert results
```

### Integration Tests

**Approach:** Test interactions between components (routers, services, database)

**Location:** `test_calendar_integration.py`, `test_routers.py`

**Example pattern:**

```python
def test_upload_file_and_retrieve(client, session):
    """Test photo upload and subsequent retrieval."""
    # Upload photo via admin endpoint
    response = client.post("/admin/upload", files={"file": ("test.jpg", image_bytes)})
    assert response.status_code == 200

    # Verify database entry
    photo = session.exec(select(Photo)).first()
    assert photo is not None
    assert photo.filename == "test.jpg"

    # Retrieve via media endpoint
    response = client.get(f"/media/image/{photo.id}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
```

**Database Isolation:**

- Each test creates a fresh in-memory SQLite database
- Tables created via `SQLModel.metadata.create_all(test_engine)`
- Tables dropped after test completion (teardown)
- Session override applied to FastAPI app via `app.dependency_overrides`

### E2E Tests (if present)

**Approach:** Not currently implemented; could use Selenium or Playwright for full browser testing

**Potential:** Testing UI interactions (HTMX swaps, form submissions, slideshow transitions)

## Test Configuration

**Location:** `conftest.py`

**Key Fixtures:**

```python
@pytest.fixture(name="session")
def session_fixture():
    """Provides isolated in-memory DB session for test."""
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session
    SQLModel.metadata.drop_all(test_engine)

@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Provides TestClient with overridden database dependency."""
    def get_session_override():
        return session
    fastapi_app.dependency_overrides[get_session] = get_session_override
    with patch("app.main.create_db_and_tables"), TestClient(fastapi_app) as client:
        yield client
    fastapi_app.dependency_overrides.clear()
```

**Configuration (pyproject.toml):**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
```

## Test Execution

**Commands:**

Run all tests:

```bash
uv run pytest tests/ -v
```

Run with coverage:

```bash
uv run pytest tests/ -v --cov=app --cov-report=xml
```

Run specific test file:

```bash
uv run pytest tests/test_calendar_service.py -v
```

Run specific test:

```bash
uv run pytest tests/test_calendar_service.py::test_parse_ics_valid -v
```

**Output Verbosity:**

- `-v` flag provides detailed test result output
- `--tb=short` provides abbreviated traceback for failures
- `--cov=app` generates coverage report for `app/` package
- `--cov-report=xml` generates XML for CI integration

## Patching Strategy

**External API Mocking:**

```python
@patch("httpx.AsyncClient.get")
async def test_weather_api_call(mock_get):
    mock_get.return_value.json.return_value = {"temperature": 20}
    result = await WeatherService.get_current_weather(45.5, -73.6)
    assert result["temp"] == 20
```

**Database Creation:**

```python
@patch("app.main.create_db_and_tables")
def test_app_startup(mock_create_db):
    # Prevents real database creation during test
    ...
```

## Coverage Targets

**Current:** Coverage tracking enabled via `--cov=app`

**Scope:** Tests cover routers, services, and model interactions

**Known Gaps:**

- Limited E2E browser testing (HTMX interactions not fully covered)
- Legacy UI rendering not extensively tested
- Weather & geocoding integrations partially mocked

**Future Goals:**

- Increase model coverage (edge cases for alarm extraction)
- Add load testing for slideshow performance
- E2E tests for admin UI (HTMX swap verification)

## Testing Best Practices Observed

1. **Fixture reuse:** `session` and `client` fixtures minimize boilerplate
2. **Dependency override:** FastAPI's built-in override mechanism ensures isolation
3. **In-memory database:** Avoids file I/O, enables parallel test execution
4. **Patching at import level:** Prevents side effects (e.g., `app.main.create_db_and_tables`)
5. **Async test support:** Uses `@pytest.mark.asyncio` for async route testing
6. **Concise test names:** Test names describe scenario being tested (e.g., `test_parse_ics_valid`)

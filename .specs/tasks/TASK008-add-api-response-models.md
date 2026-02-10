# TASK008 - Add API response models and docstrings

**Status:** Pending
**Priority:** Low
**Added:** February 10, 2026
**Updated:** February 10, 2026

## Original Request

API endpoints lack proper Pydantic response models and detailed docstrings. While the FastAPI `/docs` endpoint is available, responses aren't type-hinted and documented, making it difficult for API consumers.

## Thought Process

Response models provide:

- Automatic OpenAPI schema generation
- Type safety for responses
- Clear API contracts
- Self-documenting code

Detailed docstrings enable:

- Clear understanding of what each endpoint does
- Parameter descriptions
- Response descriptions
- Example responses

## Implementation Plan

- [ ] Create response models for weather endpoint
- [ ] Create response models for slide endpoint
- [ ] Create response models for image endpoints
- [ ] Add detailed docstrings to all routes
- [ ] Include example responses in docstrings
- [ ] Verify OpenAPI docs are complete
- [ ] Add response_model to @router decorators

## Progress Tracking

**Overall Status:** Not Started - 0%

### Subtasks

| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 8.1 | Create WeatherResponse model | Not Started | - | temp, condition fields |
| 8.2 | Create SlideResponse model | Not Started | - | HTML content |
| 8.3 | Add detailed docstring to /components/weather | Not Started | - | Parameter/response docs |
| 8.4 | Add detailed docstring to /components/slide | Not Started | - | Parameter/response docs |
| 8.5 | Add response_model to weather endpoint | Not Started | - | In decorator |
| 8.6 | Add response_model to slide endpoint | Not Started | - | In decorator |
| 8.7 | Verify OpenAPI schema is complete | Not Started | - | Check /docs |
| 8.8 | Add example requests/responses | Not Started | - | In docstrings |

## Verification Criteria

✅ All endpoints have response models
✅ Docstrings describe purpose, parameters, and responses
✅ OpenAPI schema complete and accurate
✅ Examples in docstrings match actual responses
✅ HTTPException responses documented
✅ Types clearly defined for API consumers

## Code Example

```python
from pydantic import BaseModel

class WeatherResponse(BaseModel):
    """Weather information response."""
    temp: int
    condition: str
    location: str | None = None

@router.get("/components/weather", response_model=WeatherResponse)
async def get_weather(session: Session = Depends(get_session)):
    """
    Get current weather widget HTML fragment.

    Returns current temperature and weather condition based on
    configured location (latitude/longitude in AppSettings).

    Returns:
        WeatherResponse: Current weather data

    Example:
        GET /components/weather
        Response:
            {
                "temp": 22,
                "condition": "Sunny",
                "location": "Montreal, Quebec"
            }
    """
```

## Related Files

- `app/routers/dashboard.py` (all component endpoints)
- `app/routers/admin.py` (settings endpoints)
- `tests/test_routers.py` (verify response structure)

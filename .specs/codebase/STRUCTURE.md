# Project Structure

## Root Shape

```text
espace-image/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── core/
│   ├── db/
│   ├── modules/
│   ├── routers/
│   ├── static/
│   └── templates/
├── data/
├── docs/
├── memory-bank/
├── scripts/
├── tests/
├── .github/
└── .specs/
```

## Application Package

### `app/main.py`

FastAPI entry point, lifespan management, APScheduler setup, and background sync wiring.

### `app/db/`

Shared persistence layer:

- `models.py` for SQLModel entities
- `engine.py` for engine/init logic
- `session.py` for FastAPI DB session dependency

### `app/routers/`

Shared HTTP adapters:

- `dashboard.py`
- `admin.py`
- `media.py`

### `app/modules/`

Capability-oriented modules:

- `calendar/`
- `alarms/`
- `weather/`
- `media/`
- `settings/`
- `slideshow/`
- `loader.py` as composition root

Each module follows this shape:

```text
<module>/
├── api/
│   └── interfaces.py
├── internal/
│   ├── application/
│   │   └── service.py
│   └── infrastructure/
└── loader.py
```

## Important Infrastructure Files

- `app/modules/calendar/internal/infrastructure/calendar_sync.py`
- `app/modules/weather/internal/infrastructure/weather_api.py`
- `app/modules/media/internal/infrastructure/image_ops.py`

## Frontend Files

- templates in `app/templates/`
- static assets in `app/static/`
- legacy compatibility assets under `app/templates/legacy/` and `app/static/polyfills/`

## Tests

Tests are organized by behavior and boundary.

Important current files:

- `tests/test_calendar_service.py`
- `tests/test_image_service.py`
- `tests/test_multi_alarm.py`
- `tests/test_non_time_alarm.py`
- `tests/test_routers.py`

## Storage

- SQLite database under `data/`
- uploaded media under `data/uploads/`

## Notes

- `app/services/` is not part of the active structure anymore.
- The shared router layer remains intentional.
- Module infrastructure files may be named for their role rather than a generic `repository.py` convention.

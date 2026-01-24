# Espace Image Dashboard

A FastAPI-based dashboard that serves a modern UI and a **Legacy UI** optimized for the iPad 2 (iOS 9.3.5). Ships as a containerized app with HTMX-powered interactions, calendar alarms, and weather widgets.

## Features
- **Photo Slideshow:** Rotates through user-uploaded images.
- **Legacy Mode:** Specialized frontend for iPad 2 (1024x768, no CSS Grid, resized images).
- **Calendar Alarms:** Integrates with iCloud Calendar to display pop-up alarms for events.
- **Weather:** Real-time weather widget.

## Quick Start (Local)

Requirements: Python 3.13+, [uv](https://docs.astral.sh/uv/) installed.

1) Install dependencies
```bash
uv sync
```

2) Configure environment
```bash
cp .env.example .env
# fill in credentials (calendar, weather, etc.)
```

3) Run the app
```bash
uv run uvicorn app.main:app --reload
```

## Testing

```bash
uv run pytest tests/ -v --cov=app --cov-report=xml
```

All current tests are unit/integration; no Docker build test is required.

## Docker

Local build and run with Compose (uses the multi-stage Dockerfile):
```bash
docker-compose up --build
```

The app listens on `http://localhost:8000`, mounts `./data` for uploads, and reads configuration from `.env`.

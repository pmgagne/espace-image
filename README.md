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
uv sync --dev
```

1) Run the app

```bash
uv run uvicorn app.main:app --reload
```

## Testing

```bash
uv run pytest tests/ -v --cov=app --cov-report=xml
```

All current tests are unit/integration; no Docker build test is required.

## Docker

### Using Docker Compose

```bash
docker-compose up --build
```

### Using Docker CLI

Build the image:

```bash
docker build -t espace-image:latest .
```

Run the container:

```bash
docker run -d \
  --name espace-image \
  -p 8000:8000 \
  -v ./data:/app/data \
  --restart unless-stopped \
  espace-image:latest
```

The app listens on `http://localhost:8000` and mounts `./data` for uploads.

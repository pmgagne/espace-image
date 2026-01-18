# Personal Slideshow & Dashboard App

A Python-based dashboard designed to run in a Docker container, serving a modern UI for current devices and a **Legacy UI** optimized for the iPad 2 (iOS 9.3.5).

## Features
- **Photo Slideshow:** Rotates through user-uploaded images.
- **Legacy Mode:** Specialized frontend for iPad 2 (1024x768, no CSS Grid, resized images).
- **Calendar Alarms:** Integrates with iCloud Calendar to display pop-up alarms for events.
- **Weather:** Real-time weather widget.

## Quick Start (Local)

1. **Install uv:**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install Dependencies:**
   ```bash
   uv sync
   ```

3. **Configure:**
   Copy `.env.example` to `.env` and fill in your details.
   ```bash
   cp .env.example .env
   ```

4. **Run:**
   ```bash
   uv run uvicorn app.main:app --reload
   ```

## Testing

Run the full test suite (including Docker integration tests) using `pytest`:

```bash
uv run python -m pytest tests/
```

To run only unit tests (skipping the slow Docker test):

```bash
uv run python -m pytest tests/test_app.py tests/test_routers.py tests/test_services.py
```

## Docker

1. **Build:**
   ```bash
   docker build -t slideshow-app .
   ```

2. **Run:**
   ```bash
   docker run -p 8000:8000 -v $(pwd)/data:/app/data --env-file .env slideshow-app
   ```

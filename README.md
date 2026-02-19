# Espace-Image

A FastAPI-based slideshow that serves a modern UI and a **Legacy UI** optimized for the iPad 2 (iOS 9.3.5). Ships as a containerized app with HTMX-powered interactions, calendar alarms, and weather widgets.

## ⚠️ Security Notice

**This application has NO built-in authentication.** It is designed for **internal-network-only deployment** on a trusted home or office network. See [SECURITY.md](SECURITY.md) for details and guidance on adding authentication if needed for LAN/internet exposure.

## Features

- **Photo Slideshow:** Rotates through user-uploaded images.
- **Legacy Mode:** Specialized frontend for iPad 2 (1024x768, no CSS Grid, resized images).
- **Calendar Alarms:** Integrates with iCloud Calendar and other ICS feeds to display pop-up alarms for events. All alarm logic is handled server-side using the [`icalevents`](https://icalevents.readthedocs.io/en/latest/) library for robust iCalendar parsing and recurrence support. The frontend displays rendered HTML fragments. See [ADR-2026-02-14-alarm-dataflow.md](docs/ADR/ADR-2026-02-14-alarm-dataflow.md) for architecture.
- **Weather:** Real-time weather widget.

## Agentic Workflow

This project is also an experiment to explore agentic full stack development. We use vscode with copilot for code generation. We use as much as possible the non-premium models
GPT-4.1 for planning and GPT-5 mini for coding.

We adopted the ask (if necessary)/plan (GPT 4-1)/Implement (GPT 5-mini) loop.

The actual takeout is that GPT4.1 seems good for planing and explaining, but not so good for
coding. GPT-5-mini (with the [4.1 Beast Mode](https://raw.githubusercontent.com/github/awesome-copilot/main/agents/4.1-Beast.agent.md)) agent prompt is convincing.

## Calendar Parsing Migration

**Note:** As of 2026-02-10, all calendar event parsing and recurrence logic uses the [`icalevents`](https://icalevents.readthedocs.io/en/latest/) library. The previous `icalendar` dependency has been fully removed. See [TASK011](memory-bank/tasks/TASK011-migrate-icalendar-to-icalevents.md) for migration details.

**Recent Fixes (2026-02-17):**

- Fixed recurring event caching to preserve all occurrences (e.g., biweekly events now show all dates)
- Fixed all-day event timezone handling to display correct dates in negative UTC offset timezones
- See [ADR-2026-02-17](docs/ADR/ADR-2026-02-17-recurring-events-allday-timezone-fixes.md) for technical details

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

### Code Quality & Validation

Lint and validate HTML, CSS, and JavaScript:

```bash
# Run all validators (HTML, CSS, JS)
npm run lint

# Run individual validators
npm run lint:html  # Validate HTML structure and accessibility
npm run lint:css   # Validate CSS syntax and browser compatibility
npm run lint:js    # Validate JavaScript syntax and compatibility

# Auto-fix CSS and JavaScript issues
npm run lint:fix
```

Python code is linted with Ruff:

```bash
# Check Python code
uv run ruff check .

# Auto-format Python code
uv run ruff format .
```

## CI/CD Pipeline

The project uses GitHub Actions for continuous integration and deployment:

### Automated Checks

Every push and pull request triggers:

- **Python Linting**: Ruff checks code style and formatting
- **Frontend Validation**: HTML, CSS, and JavaScript linting
  - HTML structure and accessibility (WCAG 2.1)
  - CSS syntax and browser compatibility (iOS 9.3+)
  - JavaScript ES5/ES6 compliance and compatibility
- **Unit Tests**: pytest with coverage reporting
- **Security Scanning**: Trivy vulnerability scanner
- **Docker Build**: Validation of container build

### Manual Validation

Run the same checks locally before pushing:

```bash
# Python checks
uv run ruff check .
uv run ruff format . --check

# Frontend checks
npm run lint

# Run tests
uv run pytest tests/ -v --cov=app
```

All checks must pass before merging to `main`.

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

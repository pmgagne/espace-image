# Espace-Image Instructions

## Project Overview

**Espace-Image** is a FastAPI-based slideshow application serving modern and legacy UIs (iPad 2 / iOS 9.3.5). It features photo slideshows, calendar alarms, weather widgets, and HTMX-powered admin interactions.

## Core Mandates

1. **Modern UI:** Must use modern CSS features (Grid, variables, etc.).
2. **Legacy UI (iPad 2 / iOS 9):** Must emulate the modern UI's look and feel but is tuned for iPad landscape (1024x768) and portrait (768x1024) displays.
3. **Legacy Constraints:** No ES6+ JS (use ES5), no CSS Grid (use flexbox/floats), no backdrop-filter.
4. **Tooling:** ALWAYS use `uv` for package management and command execution.

## Technical Stack

- **Backend:** FastAPI, Python 3.13+, SQLModel (SQLite)
- **Frontend:** HTMX 1.0 (ES5 build), Jinja2, vanilla CSS
- **Linting:** Ruff

## Development Commands

- `uv sync` - Install dependencies
- `uv run uvicorn app.main:app --reload` - Start dev server
- `uv run pytest` - Run tests
- `uv run ruff check --fix` - Lint and fix

## Directory Structure

- `app/routers/` - API endpoints
- `app/templates/` - Modern templates
- `app/templates/legacy/` - iPad 2 optimized templates
- `app/static/css/main.css` - Global styles
- `tests/` - pytest suite

Refer to `.github/copilot-instructions.md` for full details on coding standards and patterns.

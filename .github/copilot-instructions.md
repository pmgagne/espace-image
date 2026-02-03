# GitHub Copilot Instructions — Espace-Image

## Big picture
- FastAPI app in app/main.py: wires routers, Jinja2 templates, static files, and a lifespan that starts APScheduler for calendar sync.
- Core layers: routers (app/routers), services (app/services), SQLModel models (app/db/models.py), DB session dependency (app/db/session.py).
- Admin UI is HTMX-driven: routes under /admin/partials/* return TemplateResponse fragments; settings updates use HX-Redirect.
- Slideshow UI: / serves modern app/templates/index.html, /legacy serves iPad 2 UI; /components/* endpoints return HTML fragments.
- Calendar pipeline: CalendarService fetches ICS via httpx + backoff, caches events in CalendarEventCache, alarms rendered in dashboard routes.

## Workflows (uv only)
- Install deps: uv sync --dev
- Run app: uv run uvicorn app.main:app --reload
- Tests: uv run pytest tests/ -v --cov=app --cov-report=xml
- Lint/format: uv run ruff check .  |  uv run ruff format .

## Project-specific conventions
- Use async route handlers and Depends(get_session) for DB access (see app/routers/admin.py).
- Gallery uploads: GalleryManager.save_upload stores files and Photo rows; slideshow reads from Photo by active preset.
- Legacy compatibility: app/templates/legacy/index.html + ES5 JS only, no CSS Grid, include polyfills in app/static/polyfills.
- Don’t edit vendored JS in app/static/js/htmx.min.js unless explicitly requested.

## Integration points & config
- Calendar sources: iCloud/ICS URLs stored in CalendarSource; background sync every 10 minutes.
- Weather: WeatherService hits Open-Meteo; admin geocoding uses Nominatim (see app/routers/admin.py).
- Env flags: LOG_LEVEL (logging), WEBAPP_DEBUG (template debug flag), DATABASE_URL (SQLite by default).

## Documentation Maintenance
- Always keep the `docs/` folder up to date with any changes to database schema, business logic, algorithms, or workflows.
- Update relevant documentation files (e.g., `docs/db/DB.md`) whenever you modify models, event/alarm logic, or system patterns.
- Documentation must be clear and actionable for LLM agents and human developers.

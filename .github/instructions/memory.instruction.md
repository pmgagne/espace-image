---
applyTo: '**'
---

# Memory Bank: Espace-Image

## 2026-02-03 — Migration PWA & Branding Espace-Image

- Ajout du support PWA pour moderne, legacy et admin : manifestes dédiés, icônes SVG/PNG, service worker minimal, balises meta/link dans les templates.
- Suppression des anciens fichiers et références "gemini", tout renommé en "espaceimage".
- Documentation d’installation et note sur la conversion SVG→PNG dans `PWA-INSTALL.md`.
- Conversion SVG→PNG optimisée à faire localement (voir note et commandes dans la doc).
- Linting et formatage à faire avec `ruff` (voir instructions fournies).
- PR créée : "Add PWA support and Espace-Image icons".

### Standards et rappels
- Respecter les conventions Python (voir `python.instructions.md`).
- Toujours mettre à jour la Memory Bank après une évolution majeure ou une PR.
- Documenter les limitations techniques (ex : impossibilité d’exécuter certains outils dans l’environnement distant).

### Prochaines étapes
- Conversion SVG→PNG à finaliser localement.
- Vérifier le lint/format Python régulièrement.
- Continuer à documenter toute évolution ou décision importante ici.

## Project Context

- FastAPI-based slideshow app with calendar alarms, weather, and legacy iPad 2 support.
- Modern and legacy UIs share alarm, slideshow, and weather features.
- Uses SQLModel, HTMX, Jinja2, and browser-native date/time formatting.

## Recent Implementation: Alarm Popup
- Alarm popups show event title plus day + time on a single line.
	- Day displays as "Aujourd'hui" / "Demain" when applicable, otherwise "Weekday, D month[ YYYY]".
	- Year is omitted when the event occurs in the current year.
	- Non all-day events show a 24h time range appended to the day (e.g. "Mardi, 5 octobre 14:00–15:00").
- Backend now passes explicit `start`, `end`, and `all_day` fields for each alarm (calendar + simulated + mock).
	- HTML output embeds these as `data-start`, `data-end`, `data-allday` attributes on a single `.alarm-time.alarm-time-small` element.
- Modern UI uses `formatAlarmTimes()` (ES6) to render the single-line day+time string after HTMX swaps.
- Legacy UI uses `formatAlarmTimesLegacy()` (ES5-compatible) and calls it after XHR updates and dismiss POSTs.
- Added `.alarm-time-small` CSS (smaller font) used in both modern and legacy templates.
- Made legacy alarm popup font colors match the modern UI (`.alarm-header` and `.alarm-body` set to white).
- Tests updated: `tests/test_multi_alarm.py` now expects the mock response to include the all-day mock event (3 items).
- All tests pass locally after these changes.

## Coding Standards

- Python 3.13+, async FastAPI routes, type hints required.
- Use `uv` for package management.
- Legacy JS: ES5 only for iPad 2 compatibility.
- No localization for alarm times; browser formatting only.

## Next Steps

- Optional follow-ups:
	- Tweak separator between day and time (e.g. use " · " instead of space).
	- Add unit tests asserting presence/format of `data-start`/`data-end` attributes and rendered text.
	- Address lint suggestion `SIM102` in `app/routers/dashboard.py` to combine nested `if` into a single condition (minor cleanup).

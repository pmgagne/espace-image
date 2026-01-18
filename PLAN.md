# Implementation Plan: Personal Slideshow & Dashboard App

## 1. Goal
Develop a containerized (Docker) Python web application using FastAPI and HTMX that serves as a personal dashboard. It must feature a photo slideshow, weather widget, and calendar alarms.
**Critical Constraint:** The application must fully support an **iPad 2 (iOS 9.3.5)** via a dedicated "Legacy Mode" with optimized assets (images < 1024x768) and simplified HTML/CSS/JS.

## 2. Investigation & Analysis Strategy
*   **Status:** The project is currently empty (greenfield).
*   **Specs:** defined in `spec.md`.
*   **Key Decisions:**
    *   **"Legacy First" UI:** We will implement the base templates using widely compatible HTML/CSS (Bootstrap 3 era style or custom floats) to ensure the legacy mode is robust. Modern mode will be an enhancement, not a replacement.
    *   **Server-Side Optimization:** All image resizing happens in Python (Pillow) before reaching the client.

## 3. Strategic Phasing

### Phase 1: Foundation & Infrastructure
**Objective:** Initialize the project structure, dependency management, and database.
1.  [x] **Project Init:** Set up `pyproject.toml` with `uv`.
2.  [x] **Directory Structure:** Create the `app/` folder hierarchy.
3.  [x] **Database:** Configure SQLModel and Models (`Preset`, `Photo`, `AppSettings`, `AlarmEvent`).
4.  [x] **Docker:** Create a working `Dockerfile` (optimized) and `docker-compose.yml`.
5.  [x] **Hello World:** Create a simple FastAPI route.

### Phase 2: Core Logic (The Backend Brain)
**Objective:** Implement the business logic services with unit tests.
1.  [x] **Image Service:** `GalleryManager` and `ImageOptimizer` (Pillow).
2.  [x] **Info Service:** `WeatherService` (Mock).
3.  [x] **Calendar Service:** `CalendarService` (ICS parsing, Alarms).

### Phase 3: The Frontend (Legacy & Modern)
**Objective:** Build the user interfaces.
1.  [x] **Base Templates:** `base.html` with conditional polyfills.
2.  [x] **Legacy View (`/legacy`):** Float-based layout, HTMX polling.
3.  [x] **Modern View (`/`):** CSS Grid layout, HTMX polling.
4.  [x] **Components:** Weather, Slideshow, Alarm endpoints.

### Phase 4: Admin & Management
**Objective:** Allow user control without touching the CLI.
1.  [x] **Admin Routes:** List/Create Presets, Upload Photos.
2.  [x] **Settings UI:** Select Active Preset.

### Phase 5: Finalization
**Objective:** Production readiness.
1.  [x] **Verification:** Full `pytest` suite passing (including Docker).

## 4. Verification Strategy
*   **Automated:** `pytest` will run after every service implementation (Phase 2).
*   **Visual:** I will request you (the user) to check the generated HTML/CSS if possible, or I will use `grep` to ensure no `display: grid` leaks into legacy templates.
*   **Build:** The Docker build must pass without errors.

## 5. Risks & Mitigation
*   **Risk:** HTMX 1.x might have issues on very old WebKit (iOS 9).
    *   *Mitigation:* We will include `history-polyfill` and `promise-polyfill`. If HTMX fails, we fall back to a simple `<meta refresh>` or vanilla JS `setInterval` for the legacy slideshow.
*   **Risk:** Image resizing consumes too much CPU on the backend.
    *   *Mitigation:* Implement basic caching (save the resized version to `data/cache/` so it's only generated once per image).

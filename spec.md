# Technical Specification: Personal Slideshow & Dashboard App

## 1. Project Overview
This project aims to build a containerized Python web application that serves as a personal dashboard and photo slideshow. It is designed to run on a local network and display information (time, weather) alongside a rotating gallery of images.

A unique requirement is strict backward compatibility with an **iPad 2 (iOS 9.3.5)**, necessitating a specific "Legacy Mode" with optimized assets and simplified code.

### Core Goals
- **Passive Display:** A digital photo frame experience with full-screen photos and a subtle information overlay.
- **Admin Interface:** Manage photos, organize them into "Presets", and configure application settings.
- **Calendar Integration:** Fetch events from iCloud (ICS/CalDAV) and display intrusive "Alarm" popups for upcoming events.
- **Legacy Support:** Ensure full functionality on an iPad 2 (512MB RAM, old WebKit) via a dedicated low-resource mode.

## 2. Technical Architecture

### 2.1 Tech Stack
- **Language:** Python 3.12+
- **Package Manager:** `uv`
- **Web Framework:** FastAPI (Async support, strict typing).
- **Templating:** Jinja2 (Server-side rendering).
- **Frontend Interactivity:** HTMX (v1.x for compatibility) + Vanilla JS (with Polyfills for legacy).
- **Database:** SQLite (Embedded, zero-conf).
- **ORM:** SQLModel (Pydantic + SQLAlchemy).
- **Image Processing:** Pillow (PIL) for resizing and optimization.
- **Containerization:** Docker (Multi-stage build).

### 2.2 System Components
1.  **Web Server (FastAPI):** Serves HTML templates, static assets, and HTMX API endpoints.
2.  **Gallery Manager:** Handles file system operations, image upload, deletion, and "Preset" logic.
3.  **Image Optimizer:** Service that resizes images for the Legacy Client (Target: 1024x768).
4.  **Info Service:** Fetches Weather data and provides Time synchronization.
5.  **Calendar Watcher:** Background task that polls the iCloud calendar feed for "Alarms".

## 3. Functional Requirements (Frontpage UI)

### 3.1 Layout & Aesthetic
The frontpage is a **Passive Display** (Digital Photo Frame) designed to be attractive and readable from a distance.

- **Background:** Full-screen slideshow using high-quality images from the active preset.
- **Floating Info Box:** 
    - **Position:** Fixed at the **top-center** of the screen.
    - **Adaptability:** Responsive design supporting both **Portrait** and **Landscape** orientations while remaining top-center.
    - **Content:**
        - **Clock:** Large, clear time display.
        - **Date:** Including the month in full text (e.g., "January 18, 2026").
        - **Weather:** Current temperature and condition icon.
    - **Style (Modern):** Semi-transparent dark background (`rgba(0,0,0,0.6)`) with a blur effect (`backdrop-filter: blur(10px)`), white text, and clean typography.
    - **Style (Legacy):** Fallback to solid semi-transparent background (no blur) with `-webkit-` prefixes for positioning.

### 3.2 Feature Details
- **Photo Carousel:**
    - Rotates images automatically (default 30s).
    - Uses CSS transitions for smooth fading between slides.
- **Calendar Alarms (Popup):**
    - When an event is active/upcoming, a **Popup Overlay** appears on top of the slideshow and info box.
    - The popup must be intrusive enough to be noticed but maintain the app's aesthetic.
    - Includes a "Dismiss" button to close the alert.

## 4. Dashboard Modes

### 4.1 Modern Mode (`/`)
- Uses CSS Grid/Flexbox and `backdrop-filter`.
- Full-resolution images.
- Smooth HTMX-driven transitions (`transition: true`).

### 4.2 Legacy Mode (`/legacy`)
- **Optimized Images:** Strictly served at 1024x768 max resolution.
- **CSS Safety:** No CSS Grid; uses Floats and simple Flexbox with vendor prefixes.
- **JS Compatibility:** Polyfills for `Promise`, `fetch`, etc.
- **Performance:** Minimized DOM elements and simplified animations.

## 5. Data Models (SQLModel)

### 5.1 Entities

**`Preset`**
- `id`: int (PK)
- `name`: str
- `created_at`: datetime

**`Photo`**
- `id`: int (PK)
- `filename`: str
- `preset_id`: int (FK)
- `uploaded_at`: datetime

**`AppSettings`** (Singleton)
- `id`: int (PK)
- `active_preset_id`: int (FK, nullable)
- `weather_api_key`: str (nullable)
- `calendar_url`: str (nullable)
- `weather_location`: str (nullable)

**`AlarmEvent`**
- `id`: int (PK)
- `uid`: str (Unique Event ID)
- `trigger_time`: datetime
- `dismissed_at`: datetime (nullable)

## 6. API Design (HTMX Oriented)

- `GET /components/weather` -> HTML fragment for weather.
- `GET /components/slide` -> HTML fragment for the next slide.
- `GET /components/alarm` -> HTML fragment for alarm popup (or 204 No Content).
- `POST /api/alarms/{uid}/dismiss` -> Mark alarm as dismissed.
- `GET /images/{photo_id}?mode=legacy` -> Returns resized image.

## 7. Testing Strategy
- **Unit Tests (`pytest`):** Image resizing logic, ICS parsing, and DB CRUD.
- **Integration Tests:** Verify HTMX endpoints return valid HTML fragments.
- **Cross-Platform Validation:** Manual check on Modern browsers and Legacy WebKit (iOS 9).
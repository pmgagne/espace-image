# Technical Specification: Personal Slideshow & Dashboard App

## 1. Project Overview
This project aims to build a containerized Python web application that serves as a personal dashboard and photo slideshow. It is designed to run on a local network and display information (time, weather) alongside a rotating gallery of images.

A unique requirement is strict backward compatibility with an **iPad 2 (iOS 9.3.5)**, necessitating a specific "Legacy Mode" with optimized assets and simplified code.

### Core Goals
- **Dashboard:** Real-time clock, weather widget, and photo carousel.
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
3.  **Image Optimizer:** Middleware/Service that resizes images on-the-fly (or caches them) for the Legacy Client (Target: 1024x768, High compression).
4.  **Info Service:** Fetches Weather data (external API) and provides Time synchronization.
5.  **Calendar Watcher:** Background task that polls the iCloud calendar feed, detects upcoming events, and flags "Alarms".

### 2.3 Directory Structure
```
.
├── app/
│   ├── core/           # Config, logging, utils
│   ├── db/             # Database connection and models
│   ├── routers/        # FastAPI route handlers (endpoints)
│   ├── services/       # Business logic (Calendar, Image, Weather)
│   ├── templates/      # Jinja2 templates (includes /legacy/ subfolder)
│   ├── static/         # CSS, JS, Images (includes /polyfills/)
│   └── main.py         # App entry point
├── data/               # Persistent storage (uploaded images, sqlite db)
├── tests/              # Pytest suite
├── Dockerfile
├── pyproject.toml
└── uv.lock
```

## 3. Functional Requirements

### 3.1 Dashboard Modes
- **Modern Mode (`/`):**
    -   Full-resolution images.
    -   CSS Grid/Flexbox modern layouts.
    -   Smooth transitions.
- **Legacy Mode (`/legacy`):**
    -   **Optimized Images:** Strictly served at 1024x768 max resolution to prevent iPad 2 RAM exhaustion.
    -   **CSS Safety:** Floats or simple Flexbox with vendor prefixes (`-webkit-`). No CSS Grid.
    -   **JS Compatibility:** Polyfills for `Promise`, `fetch`, `Array.prototype.find`, etc.
    -   **Reduced DOM:** Simplified widgetry to lower rendering cost.

### 3.2 Features
- **Photo Carousel:**
    -   Rotates images from the currently active "Preset".
    -   Configurable interval (e.g., 30s, 1m).
- **Weather Widget:**
    -   Current temperature and condition icon.
    -   Simple forecast (High/Low).
- **Calendar Alarms:**
    -   Backend polls ICS feed every X minutes.
    -   Frontend polls `/api/alarms/active` every minute.
    -   If an alarm is active:
        -   Display a modal overlay (taking over the screen).
        -   "Dismiss" button sends a request to backend to acknowledge the alarm.
        -   Dismissed alarms are stored in DB to prevent reappearing.

### 3.3 Admin Panel
-   Create/Delete "Presets" (Folders).
-   Upload images to specific Presets.
-   Select the "Active Preset" for the dashboard.
-   Configure Weather API Key and iCloud Calendar URL.

## 4. Data Models (SQLModel)

### 4.1 Entities

**`Preset`**
-   `id`: int (PK)
-   `name`: str
-   `created_at`: datetime

**`Photo`**
-   `id`: int (PK)
-   `filename`: str
-   `preset_id`: int (FK)
-   `uploaded_at`: datetime

**`AppSettings`** (Singleton row)
-   `id`: int (PK)
-   `active_preset_id`: int (FK, nullable)
-   `weather_api_key`: str (nullable)
-   `calendar_url`: str (nullable)
-   `weather_location`: str (nullable)

**`AlarmEvent`**
-   `id`: int (PK)
-   `uid`: str (Unique Event ID from ICS)
-   `trigger_time`: datetime
-   `dismissed_at`: datetime (nullable)

## 5. API Design (HTMX Oriented)

### 5.1 Dashboard Endpoints
-   `GET /components/weather` -> Returns HTML fragment for weather widget.
-   `GET /components/slide` -> Returns HTML for the next slide (image + metadata).
-   `GET /components/alarm` -> Returns HTML for alarm modal if active, else empty 200 OK.
-   `POST /api/alarms/{uid}/dismiss` -> Marks alarm as dismissed.

### 5.2 Legacy Specifics
-   `GET /images/{photo_id}?mode=legacy` -> Returns resized image (generated or cached).

## 6. Testing Strategy
-   **Unit Tests (`pytest`):**
    -   Test Image resizing logic (ensure dimensions are correct).
    -   Test ICS parsing (verify event extraction).
    -   Test Database CRUD operations.
-   **Integration Tests:**
    -   Test API endpoints return correct HTML fragments.
-   **Manual Validation:**
    -   Verify CSS rendering on legacy WebKit simulator or actual device.

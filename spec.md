# Technical Specification: Personal Slideshow & Dashboard App

## 1. Project Overview
This project aims to build a containerized Python web application that serves as a personal dashboard and photo slideshow. It is designed to run on a local network and display information (time, weather) alongside a rotating gallery of images.

A unique requirement is strict backward compatibility with an **iPad 2 (iOS 9.3.5)**, necessitating a specific "Legacy Mode" with optimized assets and simplified code.

### Core Goals
- **Passive Display:** A digital photo frame experience with full-screen photos and a subtle information overlay.
- **Admin Interface:** User-friendly management of photos, presets, calendars, and weather settings via a Sidebar UI.
- **Calendar Integration:** Fetch events from multiple iCloud (WebCal) feeds and display intrusive "Alarm" popups for today's events.
- **Legacy Support:** Ensure full functionality on an iPad 2 (512MB RAM, old WebKit).

## 2. Technical Architecture

### 2.1 Tech Stack
- **Language:** Python 3.12+
- **Web Framework:** FastAPI.
- **Frontend:** HTMX + Vanilla JS (ES5 for Legacy).
- **Database:** SQLite (SQLModel/SQLAlchemy).
- **Weather API:** Open-Meteo (No API Key).
- **Calendar Parser:** `icalendar` library (Robust support for Apple/Google feeds).
- **Containerization:** Docker.

### 2.2 System Components
1.  **Web Server:** FastAPI serving Templates and JSON/HTML fragments.
2.  **Gallery Manager:** Manages file uploads, deletions, and thumbnail generation.
3.  **Calendar Service:** Aggregates events from multiple `CalendarSource` URLs (ICS/WebCal) using parallel async fetching.
4.  **Weather Service:** Fetches data from Open-Meteo using Lat/Long coordinates with WMO code mapping.

## 3. Functional Requirements

### 3.1 Admin Interface
- **Layout:** Persistent **Sidebar Navigation** with content loaded via HTMX.
- **Sections:**
    1.  **General Settings:**
        -   **Weather:** Latitude/Longitude inputs + "Find My Location".
        -   **Slideshow:** Active Preset + **Duration** (seconds).
    2.  **Calendar Sources:**
        -   List view of configured calendars (Label + URL + Color).
        -   Form to add new WebCal URLs.
    3.  **Gallery Management:**
        -   **Preset Manager:** Create new folders.
        -   **Photo Viewer:** Visual grid of thumbnails.
        -   **Upload:** Multi-file upload support.

### 3.2 Dashboard UI
- **Modern (`/`):** Full-screen, blurred overlay, CSS Grid.
- **Legacy (`/legacy`):** Absolute positioning, solid backgrounds, optimized for iOS 9.
- **Features:**
    -   **Clock/Date:** Large typography.
    -   **Weather:** Localized condition + Temp (Open-Meteo).
    -   **Alarms:** Aggregated from all sources. Shows events from the last 12 hours (Today) that haven't been dismissed.
    -   **Access:** Subtle "Admin" link on the bottom right.

## 4. Data Models (SQLModel)

### 4.1 Entities

**`Preset`**
- `id`: int (PK)
- `name`: str (Unique)
- `created_at`: datetime

**`Photo`**
- `id`: int (PK)
- `filename`: str
- `preset_id`: int (FK)
- `uploaded_at`: datetime

**`CalendarSource`**
- `id`: int (PK)
- `label`: str
- `url`: str (WebCal/ICS)
- `color`: str

**`AppSettings`** (Singleton)
- `id`: int (PK)
- `active_preset_id`: int (FK, nullable)
- `weather_latitude`: float (nullable)
- `weather_longitude`: float (nullable)
- `weather_timezone`: str (default="auto")
- `slideshow_duration`: int (default=30)

**`AlarmEvent`** (Track Dismissals)
- `id`: int (PK)
- `uid`: str (Unique Event ID)
- `trigger_time`: datetime
- `dismissed_at`: datetime

## 5. API Design

### 5.1 Admin Endpoints (Partials)
- `GET /admin/partials/settings`: Settings form.
- `GET /admin/partials/calendars`: Calendar list.
- `GET /admin/partials/gallery`: Photo grid.
- `POST /admin/settings`: Update config (Lat/Long, Duration).
- `POST /admin/upload`: Handle file uploads.

### 5.2 Dashboard Endpoints
- `GET /components/weather`: HTML fragment for weather.
- `GET /components/slide`: HTML fragment for next slide.
- `GET /components/alarm`: HTML fragment for alarm popup (checks dismissal).
- `POST /api/alarms/{uid}/dismiss`: Mark alarm as dismissed.

## 6. Testing Strategy
- **Unit Tests:** Verify `CalendarService` parsing and merging logic using `icalendar`.
- **Integration:** Test Admin HTMX flows and Dashboard component rendering.
- **Legacy:** Manual verification on iPad 2 (or simulation) for CSS/JS compatibility.
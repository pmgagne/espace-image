# Project Brief — Espace-Image

## Vision

A FastAPI-based digital photo slideshow application that transforms a tablet (particularly iPad 2) into a smart picture frame with integrated calendar alarms and weather information.

## Core Requirements

### Primary Goals

1. **Photo Slideshow**: Display user-uploaded photos in rotation with configurable timing
2. **Calendar Integration**: Show pop-up alarms for upcoming events from iCloud/ICS calendar feeds
3. **Weather Display**: Real-time weather information for configured location
4. **Legacy Device Support**: Full compatibility with iPad 2 (iOS 9.3.5) hardware

### Data Storage & Database

- **Database**: SQLite (single-file, no external DB server)
- **ORM**: SQLModel (Pydantic + SQLAlchemy)
- **Schema**: Supports photo presets, photo uploads, calendar sources, cached calendar events, alarms, and admin settings.
- **Key Tables**:
 	- AppSettings: Global config (active preset, weather, slideshow duration)
 	- Preset: Photo collections
 	- Photo: Uploaded images, linked to presets
 	- CalendarSource: ICS/WebCal URLs
 	- CalendarEventCache: Cached events (1-week window, recurring events expanded)
 	- AlarmEvent: Dismissal/trigger records
 	- CalendarSyncStatusEntry: Sync status per calendar source
- **Relationships**:
 	- Preset 1--* Photo
 	- CalendarSource 1--* CalendarEventCache
 	- CalendarSource 1--1 CalendarSyncStatusEntry
- **Time Handling**: All datetimes stored in UTC; original timezone preserved for display and recurrence logic.
- **Rationale**: SQLite is sufficient for single-family/internal use, with no need for external DB or high concurrency. Schema is optimized for fast event/album lookup and reliable alarm display.

### Target Environment

- **Deployment**: Internal network only (home/office LAN)
- **Security Model**: No authentication (trusted network assumption)
- **Primary Hardware**: iPad 2 (1024x768, iOS 9.3.5, Safari with ES5 JavaScript)
- **Modern Fallback**: Desktop/mobile browsers with modern ES6+ support

### Success Criteria

1. iPad 2 can run 24/7 without crashes or memory issues
2. Calendar alarms display reliably with < 1 minute latency
3. Photo uploads work seamlessly via admin interface
4. Weather and alarm data refresh together every 5 minutes (configurable)
5. No manual intervention needed after initial setup

6. Database schema supports all core features, with reliable event caching, alarm tracking, and photo management.

## Scope

### In Scope

- Slideshow with multiple photo presets
- iCloud/Google Calendar/ICS feed integration
- Weather widget (Open-Meteo API)
- Admin web interface for configuration
- Legacy mode for iPad 2 (ES5, basic CSS)
- Modern mode for current browsers (ES6+, CSS Grid)
- Docker deployment for easy installation

### Out of Scope

- Multi-user accounts or authentication (internal network only)
- Photo editing/filters/effects
- Video playback
- Social media integration
- Mobile app (PWA only)
- Calendar event creation/modification (read-only)

## Constraints

### Technical

- Must run on Python 3.13+
- Must support Safari on iOS 9.3.5 (WebKit 600.1.4)
- HEIC/HEIF image format support for iPhone photos
- Minimal external dependencies

### Performance

- Image optimization for iPad 2 memory limits (<1MB per image)
- Fast page loads on legacy hardware (< 2 seconds)
- Efficient background sync (calendar: 3 hours, UI: 5-minute intervals for weather/alarms)
- Low CPU usage during idle display

- Database queries and writes optimized for low-latency alarm/event/photo access.

### Deployment

-Container-ready (Docker + Docker Compose)

- File-based storage (no cloud dependencies)
- Simple configuration via environment variables
- No internet exposure (internal network only)

## Key Decisions

1. **FastAPI over Flask/Django**: Async support, automatic API docs, modern Python type hints
2. **HTMX over React/Vue**: Simplicity, no build step, minimal JavaScript
3. **SQLModel over raw SQLAlchemy**: Combined Pydantic validation + ORM
4. **icalevents over icalendar**: Higher-level API, built-in recurrence handling
5. **No authentication**: Internal network deployment model documented in SECURITY.md
6. **Dual UI strategy**: Modern SPA + Legacy fallback for maximum compatibility

7. **SQLite for DB**: Chosen for simplicity, reliability, and suitability for single-user/home deployment. Schema designed for extensibility and fast lookups.

## Success Metrics

- Uptime: >99% on dedicated hardware
- Alarm accuracy: 100% of events displayed within 1 minute of trigger time
- Image optimization: <1MB per rendered image for iPad 2
- Calendar sync reliability: <0.1% failure rate over 1 month
- User satisfaction: Family use without technical support needed

## Related Documents

- [README.md](../README.md) — Installation and quick start
- [SECURITY.md](../SECURITY.md) — Security model and deployment guidance
- [.specs/codebase/ARCHITECTURE.md](../.specs/codebase/ARCHITECTURE.md) — Technical architecture
- [docs/ADR/](../docs/ADR/) — Architectural decision records

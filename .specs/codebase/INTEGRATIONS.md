# External Integrations

## Calendar Sources (WebCal/ICS)

**Service:** User-provided ICS URLs (iCloud, Google Calendar, Nextcloud, etc.)
**Purpose:** Fetch calendar events and display upcoming alarms
**Implementation:** `app/services/calendar_service.py`
**Configuration:** Admin UI → Settings panel → Add Calendar Source (URL + label + color)

### Data Flow

```
CalendarSource (row with URL)
    ↓ (every 10 minutes via APScheduler)
CalendarService.sync_calendar_events()
    ├─ Fetch ICS via httpx with backoff retry (exponential, max 5 attempts)
    ├─ Parse with icalendar library (VEVENT entries, VALARM entries)
    ├─ Extract alarm trigger times (TRIGGER property in VALARM)
    ├─ Cache events in CalendarEventCache (1-week sliding window)
    ├─ Create AlarmEvent rows for upcoming alarms
    ├─ Update CalendarSyncStatusEntry (last_synced_at, next_sync_at, status)
    └─ On error: log exception, increment error_count, store error_message
```

### Authentication

- **Type:** Not required for public ICS URLs (iCloud, Google Calendar public links)
- **Headers:** User-Agent header included for politeness (`httpx.AsyncClient` default)
- **Error Handling:** Backoff retry on transient failures; graceful fallback on permanent failures

### Key Models

- `CalendarSource`: URL storage (id, label, url, color)
- `CalendarEventCache`: Cached entries (calendar_source_id, uid, summary, event_start/end, description, location)
- `AlarmEvent`: Extracted alarms (uid, trigger_time, dismissed_at)
- `CalendarSyncStatusEntry`: Sync metadata (calendar_source_id, last_synced_at, next_sync_at, sync_status, error_message, error_count)

### Calendar Event Details Parsed

- **Event fields:** summary, description, location, start time, end time
- **Alarms:** VALARM entries with TRIGGER property (time-based e.g., "-PT15M" = 15 min before; non-time-based e.g., "RELATED=START")
- **Recurrence:** Recurring events handled via dateutil.rrule (RFC 5545 RRULE support)

### Limitations & Considerations

- No authentication required (assumes public calendars or user provides public share links)
- Sync window limited to ~1 week (to prevent unbounded storage)
- Alarm deduplication via UID (calendar event + alarm combination)
- Non-time alarms (e.g., "at event start") handled separately from time-based alarms

## Weather Data (Open-Meteo API)

**Service:** Open-Meteo (free, no authentication required)
**Purpose:** Display current weather on slideshow
**Implementation:** `app/services/weather_service.py`
**Configuration:** Admin UI → Settings → Search Location (geocoding via Nominatim)

### API Integration

```python
WeatherService.get_current_weather(latitude: float, longitude: float)
    ↓
GET https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code
    ↓
Parse response:
    - temperature_2m (current temperature in °C)
    - weather_code (WMO code mapped to human-readable condition)
    ↓
Return: {"temp": value, "condition": string}
```

### Configuration

- **Coordinates:** Stored in `AppSettings` (weather_latitude, weather_longitude)
- **Timezone:** `AppSettings.weather_timezone` (default "auto"; used for sunrise/sunset if extended)
- **Update Interval:** Real-time per request (no caching of weather data)

### Display

- **Component:** `/components/weather` endpoint returns HTML fragment
- **Rendered:** In both modern and legacy slideshow UIs
- **Format:** Temperature + condition (e.g., "22°C - Sunny")

### Limitations

- No API key required (rate limits apply: ~10 requests/min per IP)
- Timezone handling basic (stored but not heavily used in current implementation)
- Weather code translation basic (uses simplified WMO code mapping)

## Geocoding (Nominatim / OpenStreetMap)

**Service:** Nominatim (OpenStreetMap reverse/forward geocoding)
**Purpose:** Convert location names to coordinates; convert coordinates to location names
**Implementation:** `app/routers/admin.py` (search endpoint) + `app/services/weather_service.py`
**Configuration:** Manual search in admin settings panel

### Forward Geocoding Flow

```
Admin: Enter location name (e.g., "Montreal")
    ↓
POST /admin/settings/search
    ↓
Nominatim forward search:
GET https://nominatim.openstreetmap.org/search?q=Montreal&format=json
    ↓
Returns: lat/lon, address details
    ↓
Form pre-populated with coordinates (user clicks "Save")
    ↓
POST /admin/settings (final save)
```

### Reverse Geocoding Flow

```
Coordinates stored in AppSettings
    ↓
GET /admin/partials/settings
    ↓
Reverse geocode display name:
GET https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json
    ↓
Extract: city, state/region, country
    ↓
Display: "{city}, {state}" (e.g., "Montreal, Quebec")
```

### Authentication

- **Type:** None required
- **Headers:** User-Agent header included (`User-Agent: Espace-Image/1.0`)

### Error Handling

```python
try:
    resp = await client.get(url, headers=...)
    data = resp.json()
    # Extract location
except Exception as e:
    logger.exception(f"Geocoding error: {e}")
    location_name = ""  # Fallback to empty
```

### API Constraints

- Rate limit: ~1 request per second (admin UI respects this)
- Timeout: 30 seconds (via httpx default or explicit settings)
- No uptime SLA (but generally reliable)

## Background Job Scheduling (APScheduler)

**Service:** APScheduler AsyncIOScheduler
**Purpose:** Automatic calendar synchronization every 10 minutes
**Implementation:** `app/main.py` (lifespan context manager)

### Job Configuration

```python
scheduler.add_job(
    background_sync_calendars,        # Async function
    "interval",                        # Trigger type
    minutes=10,                        # Interval
    id="calendar_sync",
    name="Sync calendar events every 10 minutes",
    next_run_time=datetime.now(),      # Start immediately
)
```

### Lifecycle

- **Startup:** Scheduled in FastAPI lifespan startup
- **Runtime:** Executes in background thread (AsyncIOScheduler runs in same event loop)
- **Shutdown:** Scheduler shutdown on app termination (graceful)

### Error Handling

```python
async def background_sync_calendars():
    session = Session(engine)
    try:
        await CalendarService.sync_calendar_events(session)
    except Exception as e:
        logger.exception(f"Error in background calendar sync: {e}")
    finally:
        session.close()  # Ensure session cleanup
```

## Image Processing & Storage

**Service:** Pillow + pillow-heif
**Purpose:** Validate uploads, resize to multiple resolutions, store in data/uploads/
**Implementation:** `app/services/image_service.py::GalleryManager`

### Upload Flow

```
Admin: POST /admin/upload (multipart/form-data)
    ├─ File part: file (binary image)
    ├─ Form data: preset_id (folder organization)
    ↓
GalleryManager.save_upload()
    ├─ Validate extension (JPEG, PNG, HEIF)
    ├─ Convert HEIF to JPEG if needed
    ├─ Create resized versions:
    │   ├─ thumbnail (small preview)
    │   ├─ display (slideshow size)
    │   └─ full (original quality, large)
    ├─ Create preset folder if needed (data/uploads/{preset_name}/)
    ├─ Save files to disk
    ├─ Create Photo record in database
    ├─ Return HTML fragment (updated gallery preview)
    ↓
HTMX: Swap gallery panel with updated list
```

### Image Resizing Strategy

- **Thumbnail:** ~200px dimension (quick preview in admin)
- **Display:** ~1024px dimension (slideshow rendering)
- **Full:** Original size (fallback, quality preservation)
- **Format:** JPEG (unless PNG explicitly required)

### Storage Structure

```
data/uploads/
├── Default/
│   ├── img_1.jpg (display version)
│   ├── img_1_thumb.jpg
│   ├── img_1_full.jpg
│   └── ...
├── Noël/
│   └── ...
└── {preset_name}/
    └── ...
```

## HTTP Client Configuration (httpx)

**Library:** httpx 0.28.1
**Usage:** External API calls (weather, geocoding, calendar fetching)

### Common Patterns

**With backoff retry:**

```python
@backoff.on_exception(
    backoff.expo,
    (httpx.HTTPError, OSError),
    max_tries=5,
    on_backoff=_on_backoff,
    on_giveup=_on_giveup,
)
async def _fetch_ics_with_retry(url: str) -> str | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text
```

**Timeout & Headers:**

```python
async with httpx.AsyncClient() as client:
    resp = await client.get(
        url,
        timeout=30,
        headers={"User-Agent": "Espace-Image/1.0"}
    )
```

### Async Usage

- All HTTP calls are async (non-blocking)
- Used in services and routers (both async functions)
- Enables concurrent requests within background jobs and route handlers

## Summary Table

| Service | URL/Endpoint | Auth | Purpose | Error Handling | Refresh |
|---------|--------|------|---------|---|---|
| Calendar ICS | User-provided URL | None | Event storage | Backoff retry × 5 | Every 10 min |
| Open-Meteo | api.open-meteo.com | None | Weather data | Exception log | Per-request |
| Nominatim | nominatim.openstreetmap.org | None | Geocoding | Exception log | Per-search |
| Local Storage | data/uploads/ | N/A | Photo storage | File I/O error handling | On upload |
| APScheduler | In-process | N/A | Job scheduling | Exception log | Every 10 min |

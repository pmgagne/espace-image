# Strategic Plan: Admin Interface Overhaul

## 1. Understanding the Goal
The objective is to transform the Admin interface into a user-friendly, SPA-like experience using HTMX.
**Key Deliverables:**
-   **Sidebar Navigation:** Persistent navigation for distinct sections.
-   **Visual Gallery Management:** Thumbnail grid with delete functionality.
-   **Multi-Calendar Support:** Manage multiple WebCal URLs with labels.
-   **Open-Meteo Integration:** Configuration via Latitude/Longitude with a "Find My Location" helper.

## 2. Investigation & Analysis
**Files Analyzed:**
-   `app/db/models.py`: Needs significant schema updates (`CalendarSource`, `AppSettings`).
-   `app/routers/admin.py`: Currently monolithic; needs endpoints for HTMX partials.
-   `app/templates/admin.html`: Will be refactored into a layout shell + partials.

**Critical Decisions:**
-   **Database Migration:** Since we are in early dev, we will update `init_db.py` to handle the new schema. Existing data might be lost unless manually migrated, which is acceptable for this prototype phase.
-   **HTMX Strategy:** We will use `hx-get` to swap the main content area (`#admin-content`) when clicking sidebar links. Forms will use `hx-post` to update specific sections without full reloads.

## 3. Proposed Strategic Approach

### Phase 1: Database Schema Update [DONE]
*   [x] **Modify `models.py`**:
    *   [x] Added `CalendarSource` model.
    *   [x] Updated `AppSettings` (replaced API key/Location string with Lat/Long).
*   [x] **Update `init_db.py`**: Updated to seed the new settings structure.
*   [x] **Action**: Re-initialized the database successfully.
*   [x] **Refactoring**: Updated `WeatherService` and `dashboard.py` to use new Lat/Long fields.

### Phase 2: Backend Routes (Admin API) [DONE]
*   [x] **Refactor `app/routers/admin.py`**:
    *   [x] Created endpoints that return **HTML Fragments** (`/partials/settings`, `/partials/calendars`, `/partials/gallery`).
    *   [x] Implemented logic for fetching partials.
*   [x] **Implement CRUD Logic**:
    *   [x] Add/Delete Calendar Sources (Backend logic ready, awaiting frontend form).
    *   [x] Delete Photos.
    *   [x] Update Lat/Long.
*   **Verification**:
    *   [x] Updated tests to expect partial responses.
    *   [x] Created placeholder templates to pass router logic tests.

### Phase 3: Frontend Templates & Interactivity [DONE]
*   [x] **Create `admin_base.html`**: Implemented shell with Sidebar and `hx-get` navigation.
*   [x] **Implement Partials**:
    *   [x] `partials/settings.html`: Settings form with JS Geolocation.
    *   [x] `partials/calendars.html`: List + Add form for multi-calendar support.
    *   [x] `partials/gallery.html`: Preset selector, Upload, and Photo Grid.
*   [x] **Styling**: Applied dark mode CSS with Flexbox layout.

### Phase 4: Integration & Testing [DONE]
*   [x] **Weather Service**: Updated to use `latitude`/`longitude` from DB.
*   [x] **Calendar Service**: 
    *   [x] Implemented `get_all_alarms` to fetch from multiple URLs in parallel.
    *   [x] Added protocol replacement (`webcal://` -> `https://`).
    *   [x] Connected `dashboard.py` to fetch active sources from DB.
*   [x] **Verification**:
    *   [x] Created `tests/test_calendar_integration.py` to verify fetching logic (mocked).
    *   [x] Confirmed timezone-aware handling for ICS comparisons.

### Phase 5: Legacy Optimization & Polish [DONE]
*   [x] **Legacy Dashboard (`/legacy`)**:
    *   [x] Replaced HTMX with Vanilla ES5 (`XMLHttpRequest`, `setInterval`) to solve loading issues on iPad 2.
    *   [x] Localized Date/Time to French.
*   [x] **Legacy Admin Support**:
    *   [x] Downgraded HTMX to 1.0.0 (Pure ES5).
    *   [x] Added `promise-polyfill` and `whatwg-fetch` locally.
    *   [x] Replaced CSS Grid with Flexbox/Floats in Admin templates.
    *   [x] Replaced all ES6 syntax (`const`, arrow functions) with ES5.
*   [x] **UX Enhancements**:
    *   [x] **Auto-Redirect**: Server detects iPad 2 (iOS 9) and redirects to `/legacy`.
    *   [x] **Location Search**: Added Open-Meteo Geocoding to Settings (enter city name -> get coords).
    *   [x] **Manual Fallback**: Added "Legacy Mode" link to modern dashboard.

## 4. Verification Strategy
*   **Database**: Check `sqlite3 data/db.sqlite ".schema"` to confirm new tables.
*   **UI Navigation**: Click sidebar links; ensure only the content area updates.
*   **Functionality**:
    *   Upload a photo -> Verify it appears in the grid.
    *   Add a Calendar -> Verify it shows in the list.
    *   Click "Find My Location" -> Verify Lat/Long inputs are populated.

## 5. Anticipated Challenges
*   **Browser Geolocation**: Requires HTTPS in some contexts (though usually works on localhost).
*   **HTMX History**: Managing browser back button with partial swaps (we might ignore this for a simple admin panel or use `hx-push-url`).
*   **Data Migration**: Breaking changes to the DB schema will require a fresh start.

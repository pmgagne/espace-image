# Strategic Plan: "Passive Display" Frontpage Overhaul

## 1. Understanding the Goal
The objective is to transform the application's frontpage into a "Passive Display" optimized for viewing from a distance.
**Key Deliverables:**
-   **Full-Screen Slideshow:** High-quality background images.
-   **Floating Info Box:** A top-center overlay displaying Time, Date (textual), and Weather.
-   **Calendar Alerts:** Intrusive "Alarm" popups for upcoming events.
-   **Legacy Compatibility:** A functional fallback for iPad 2 (iOS 9.3.5).

## 2. Investigation & Analysis
**Files Analyzed:**
-   `app/services/weather_service.py`: Mock data is sufficient for UI dev.
-   `app/routers/dashboard.py`: Returns raw HTML strings. These need to be updated to match the new CSS class structures.
-   `app/templates/index.html` & `app/templates/legacy/index.html`: Need complete structural rewrites.

**Critical Decisions:**
-   **CSS Strategy:** We will use a `style` block in the head (or inline in `base.html` if shared) to keep it simple, but specific overrides in `index.html` vs `legacy/index.html`.
-   **Responsive Design:** The "Floating Info Box" will use `position: fixed; top: 20px; left: 50%; transform: translateX(-50%);` to ensure it stays centered in both Portrait and Landscape.
-   **Legacy Fallback:** iPad 2 will use `position: absolute` and standard opacity instead of `backdrop-filter`.

## 3. Proposed Strategic Approach

### Phase 1: Backend & Component Logic [DONE]
*   [x] **Update `dashboard.py`**:
    *   [x] Modified `/components/weather` to return the HTML structure for the "Floating Info Box" (ready for styling).
    *   [x] Modified `/components/alarm` to return a mock full-screen Modal overlay structure when `?mock=true`.
    *   [x] Updated `/components/slide` to use consistent CSS classes (`slide-container`, `full-slide`).
*   **Implementation Notes**:
    *   Components now return semantic HTML fragments that align with the "Passive Display" strategy.
    *   Mocking support added to `/components/alarm` for easier frontend development of the popup.

### Phase 2: Modern Frontend (`index.html`) [DONE]
*   [x] **Layout Implementation**:
    *   [x] Removed Grid/Sidebar; implemented `fixed` full-screen container for slideshow.
    *   [x] Implemented Top-Center "Info Box" container (`fixed`, `transform: translate(-50%)`).
*   [x] **Styling**:
    *   [x] Applied `backdrop-filter: blur(15px)` and semi-transparent backgrounds.
    *   [x] Typography: Thin, large font for clock; distinct uppercase style for date.
*   [x] **Interactivity**:
    *   [x] Added Vanilla JS to update Clock and Date (Month Text) every second.
    *   [x] Configured HTMX triggers for Slide (30s), Weather (10m), and Alarm (10s).
*   **Implementation Notes**:
    *   Used CSS `z-index` layering: Slideshow (0) < Info Box (10) < Alarm Modal (100).
    *   Added HTMX transition support logic in CSS.

### Phase 3: Legacy Frontend (`legacy/index.html`) [DONE]
*   [x] **Layout Adaptation**:
    *   [x] Mimicked the Top-Center Info Box using `position: absolute` and `transform` (supported in iOS 9).
    *   [x] Removed `backdrop-filter`; used solid semi-transparent background (`rgba(0,0,0,0.7)`).
*   [x] **Polyfills**:
    *   [x] Used Vanilla JS (ES5) for the Clock to ensure compatibility without transpilation.
    *   [x] Verified structure with `curl`.
*   **Implementation Notes**:
    *   Used `display: table` centering for the Alarm modal as a robust fallback.
    *   Explicit `-webkit-` prefixes added where relevant (though most used properties are standard in iOS 9.3).

### Phase 4: Calendar Alarm Integration [DONE]
*   [x] **Mock Data**:
    *   [x] Verified `?mock=true` endpoint returns the Alarm Modal HTML.
*   [x] **Dismiss Logic**:
    *   [x] Updated `/api/alarms/{uid}/dismiss` to return an empty string.
    *   [x] Verified with `curl` that it effectively "removes" the modal (by swapping it with nothing).
*   **Implementation Notes**:
    *   The backend logic for the Alarm Popup is now fully supported by the frontend's HTMX loop.
    *   Dismissal works by swapping the modal's `outerHTML` with an empty string.

## 4. Verification Strategy
*   **Visual Validation**:
    *   Does the Info Box stay centered when resizing the window (simulating rotation)?
    *   Is the text readable over dark/light images?
*   **Functional Testing**:
    *   Wait for 1 minute to see the minute hand change.
    *   Wait for slide transition (30s).
    *   Trigger the mock alarm and verify the popup appears.

## 5. Anticipated Challenges
*   **Image Aspect Ratios**: "Cover" fit might crop important parts of photos. We will accept this trade-off for the "modern" look but might use "contain" for Legacy if performance/cropping is an issue.
*   **HTMX Swapping**: Replacing the slide might cause a "flash" of white. We will use CSS transitions (`opacity`) to mitigate this.
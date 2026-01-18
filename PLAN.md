# Strategic Plan: Persistent Bottom-Center Alarm Box

## 1. Understanding the Goal
The objective is to redesign the Calendar Event (Alarm) popup to:
*   **Visual Style:** Match the existing "Clock Box" (semi-transparent black, rounded corners).
*   **Position:** Bottom-Center of the screen.
*   **Behavior:** Non-blocking (no full-screen overlay), allowing the slideshow to be visible.
*   **Multi-Event:** Display *all* active events simultaneously in the same box.
*   **Compatibility:** Must work on both Modern (Blur, Flexbox/Grid) and Legacy (iPad 2, Absolute positioning, No Blur) dashboards.

## 2. Investigation & Analysis
**Current State:**
*   **Backend (`dashboard.py`):** `check_alarm` fetches alarms but stops at the first undismissed one. It returns a full-screen modal HTML string.
*   **Modern UI:** Uses `.alarm-modal` with `position: fixed; top: 0; left: 0; width: 100vw; height: 100vh` and a pulsing red background.
*   **Legacy UI:** Uses similar full-screen blocking styles.
*   **Dismissal:** Uses HTMX (`hx-post`) to swap the overlay content.

**Required Changes:**
1.  **Backend:** Modify `check_alarm` to iterate through *all* active alarms and return them as a list.
2.  **HTML Structure:** The returned HTML must be a container (styled like the clock) with a list of event items.
3.  **CSS:**
    *   Remove full-screen overlay styles.
    *   Apply `.info-box-container` styles to the alarm container.
    *   Position at `bottom: 3vh` (Modern) / `bottom: 20px` (Legacy).
4.  **Interaction:** Dismiss buttons need to trigger a refresh of the alarm container to remove the dismissed item (or remove the specific item from the DOM).

## 3. Proposed Strategic Approach

### Phase 1: Backend Logic (Multi-Alarm Support) [DONE]
*   [x] **Modify `app/routers/dashboard.py`**:
    *   [x] Update `check_alarm` to collect a list of *all* undismissed `active_alarms`.
    *   [x] Update the returned HTML template to iterate over this list.
    *   [x] If the list is empty, return an empty string.
    *   [x] Structure the HTML to be a `div` with class `alarm-container` containing multiple `alarm-item` divs.

### Phase 2: Modern Styling (`app/templates/index.html`) [DONE]
*   [x] **Update CSS**:
    *   [x] Define `.alarm-box-container` class that mirrors `.info-box-container`.
    *   [x] Position it at `bottom: 5vh; left: 50%; transform: translateX(-50%)`.
    *   [x] Style `.alarm-item` to look clean (e.g., small header, description, dismiss button).
    *   [x] Remove the old `.alarm-modal` styles.

### Phase 3: Legacy Styling (`app/templates/legacy/index.html`)
*   **Update CSS**:
    *   Define `.alarm-box-container` mirroring the legacy `.info-box-container`.
    *   Position at `bottom: 60px` (above the admin link).
    *   Ensure no Flexbox/Grid is used for the container itself if absolute positioning works better for the "stack".

### Phase 4: Interaction Refinement [DONE]
*   [x] **Dismissal**:
    *   [x] The `dismiss_alarm` endpoint now returns the updated alarm list instead of an empty string.
    *   [x] The frontend targets the `#alarm-poller` (Modern) or `#alarm-wrapper` (Legacy) to refresh the whole list immediately.
    *   [x] **Implementation Note**: Added "Smart Swap" logic to both dashboards (Modern via `htmx:afterRequest`, Legacy via `lastAlarmHtml` tracker) to prevent repetitive `slideUp` animations when content hasn't changed.
    *   [x] **Implementation Note**: Synchronized background transparency and blur with the clock/weather info box.

## 4. Verification Strategy
*   **Mock Data**: Use the `?mock=true` endpoint to simulate multiple alarms.
*   **Visual Check (Modern)**: Verify the box appears at the bottom, matches the clock style, and the slideshow plays behind it.
*   **Visual Check (Legacy)**: Verify on iPad 2 (or simulation) that the box is centered, legible, and doesn't crash the browser.
*   **Functional Check**: Dismiss one event -> Box updates (removes item). Dismiss last event -> Box disappears.

## 5. Anticipated Challenges & Considerations
*   **Vertical Space**: If there are many events, the box might grow too large. We should implement a `max-height` with `overflow-y: auto` (hidden scrollbar) or just limit to showing the top 3.
*   **Legacy CSS**: Vertical centering of text vs content in absolute positioning can be tricky on iOS 9. Sticking to simple block stacking is safest.
*   **Z-Index**: Ensure the alarm box is above the slideshow (`z=0`) but below any actual system overlays. `z=20` should suffice (Clock is `z=10`).
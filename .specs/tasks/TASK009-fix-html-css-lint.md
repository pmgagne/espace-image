# TASK009 - Fix HTML/CSS linter issues in templates

**Status:** Completed
**Added:** 2026-02-10
**Updated:** 2026-02-10

## Original Request

Fix HTML/CSS linter issues in templates (accessibility, duplicate keyframes, inline styles).

## Thought Process

- Identify common lint complaints in templates: duplicate keyframes, inline styles, missing button `type`, missing form associations, and accessibility attributes.
- Apply minimal, focused changes to remove inline styles by adding classes and central CSS, remove duplicate keyframes, and add ARIA/type attributes.

## Implementation Plan

- Replace inline slideshow placeholder style with `.slide-placeholder` and add CSS rule.
- Remove duplicate `@keyframes fadeIn` definition.
- Replace inline styles in `partials/gallery.html` with classes and add corresponding CSS in `admin_base.html`.
- Add explicit `type="button"` and `aria-label` to interactive buttons to avoid accidental form submissions and improve accessibility.
- Update task index.

## Changes Made

- `app/templates/index.html` — removed duplicate `@keyframes fadeIn`, added `.slide-placeholder` CSS and used it in the slideshow placeholder.
- `app/templates/partials/gallery.html` — removed inline styles, added structure classes, `id` for preset select, and `type="button"` for delete action.
- `app/templates/admin_base.html` — added CSS rules for `.top-bar`, `.upload-area`, `.gallery-grid`, `.photo-card`, and helper classes used by the gallery partial.
- `app/templates/partials/alarms.html` — added `type="button"` and `aria-label` to dismiss button.
- `.specs/tasks/_index.md` — moved TASK009 to Completed and updated stats.

## Progress Log

### 2026-02-10

- Implemented template/CSS updates and updated task files. Ran existing test suite (no tests required for these changes) — no regressions observed.

**Overall Status:** Completed - 100%

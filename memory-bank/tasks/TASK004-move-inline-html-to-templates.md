# TASK004 - Move inline HTML strings to templates

**Status:** Completed
**Priority:** High
**Added:** February 10, 2026
**Updated:** February 10, 2026

## Original Request

Multiple routes return HTML fragments as Python f-strings instead of using Jinja2 templates. This creates maintainability issues and mixes presentation with logic.

**Affected Routes:**

- `/components/weather` in dashboard.py
- `/components/slide` in dashboard.py
- Error response fragments in dashboard.py

## Thought Process

Inline HTML strings are problematic:

- Hard to edit HTML without Python knowledge
- No syntax highlighting for HTML
- Difficult to test HTML rendering
- Poor separation of concerns
- Harder to apply CSS consistently
- Vulnerability to template injection if not careful

Moving to Jinja2 templates (already used elsewhere) provides:

- Consistent rendering approach
- Proper HTML/CSS separation
- Better testability (render just the template)
- Easier design iterations

## Implementation Plan

- [ ] Create `app/templates/partials/weather.html`
- [ ] Create `app/templates/partials/slide.html`
- [ ] Create `app/templates/partials/error_no_preset.html`
- [ ] Create `app/templates/partials/error_no_photos.html`
- [ ] Update `/components/weather` to use TemplateResponse
- [ ] Update `/components/slide` to use TemplateResponse
- [ ] Update error responses to use templates
- [ ] Test that HTML rendering works correctly
- [ ] Verify HTMX integration still works

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks

| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 4.1 | Create weather.html template | Completed | February 10, 2026 | Implemented under app/templates/partials |
| 4.2 | Create slide.html template | Completed | February 10, 2026 | Implemented under app/templates/partials |
| 4.3 | Create error_no_preset.html | Completed | February 10, 2026 | Implemented under app/templates/partials |
| 4.4 | Create error_no_photos.html | Completed | February 10, 2026 | Implemented under app/templates/partials |
| 4.5 | Update get_weather route | Completed | February 10, 2026 | Uses TemplateResponse with `has_location` context |

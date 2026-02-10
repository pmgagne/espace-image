# TASK004 - Move inline HTML strings to templates

**Status:** Pending
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

**Overall Status:** Not Started - 0%

### Subtasks

| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 4.1 | Create weather.html template | Not Started | - | With weather data context |
| 4.2 | Create slide.html template | Not Started | - | With photo, mode context |
| 4.3 | Create error_no_preset.html | Not Started | - | Friendly error message |
| 4.4 | Create error_no_photos.html | Not Started | - | Friendly error message |
| 4.5 | Update get_weather route | Not Started | - | Use TemplateResponse |
| 4.6 | Update get_next_slide route | Not Started | - | Use TemplateResponse |
| 4.7 | Test weather endpoint HTML output | Not Started | - | Verify structure |
| 4.8 | Test slide endpoint HTML output | Not Started | - | Verify img tag |

## Verification Criteria

✅ All HTML moved from Python strings to Jinja2 templates
✅ Templates in `app/templates/partials/`
✅ TemplateResponse used with proper context variables
✅ HTML structure identical to original (just moved)
✅ HTMX swap still works correctly
✅ Tests verify rendered HTML contains expected elements
✅ No inline HTML strings remain in routers

## Template Examples

**weather.html:**

```html
<div id="weather-display" class="weather-info">
    <span class="temp">{{ weather.temp }}°C</span>
    <span class="condition">{{ weather.condition }}</span>
</div>
```

**slide.html:**

```html
<div class="slide-container fade-in">
    <img src="/images/{{ photo.id }}?mode={{ mode }}" class="full-slide" alt="Slide">
</div>
```

## Related Files

- `app/routers/dashboard.py` (lines 47-77 and others)
- `app/templates/partials/` (create new templates)
- `tests/test_routers.py` (update tests)

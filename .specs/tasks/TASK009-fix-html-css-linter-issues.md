# TASK009 - Fix HTML/CSS linter issues in templates

**Status:** Pending
**Priority:** Low
**Added:** February 10, 2026
**Updated:** February 10, 2026

## Original Request

HTML linter identifies several CSS and HTML structure issues in templates:

- Inline styles should be external CSS
- Vendor prefix ordering (-webkit-backdrop-filter before backdrop-filter)
- Apple touch icon in body instead of head
- Deprecated CSS properties

## Thought Process

While these aren't functional bugs, they represent code quality issues:

- Inline styles are harder to maintain
- Correct vendor prefix order improves readability
- Proper HTML structure is semantically correct
- Deprecated properties may stop working in future browser versions

## Implementation Plan

- [ ] Create external CSS file for inline styles
- [ ] Move inline style attributes to CSS classes
- [ ] Fix vendor prefix ordering in index.html
- [ ] Fix vendor prefix ordering in legacy/index.html
- [ ] Move apple-touch-icon to <head>
- [ ] Remove deprecated -webkit-overflow-scrolling
- [ ] Verify styles still apply correctly
- [ ] Test in both modern and legacy UIs

## Progress Tracking

**Overall Status:** Not Started - 0%

### Subtasks

| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 9.1 | Create app/static/css/inline.css | Not Started | - | For extracted styles |
| 9.2 | Extract inline styles from index.html | Not Started | - | Line 320 and others |
| 9.3 | Extract inline styles from legacy/index.html | Not Started | - | Line 231 and others |
| 9.4 | Fix -webkit-backdrop-filter order (index) | Not Started | - | Line 87, 124 |
| 9.5 | Fix -webkit-backdrop-filter order (legacy) | Not Started | - | Related lines |
| 9.6 | Move apple-touch-icon to <head> | Not Started | - | Both templates |
| 9.7 | Remove -webkit-overflow-scrolling | Not Started | - | Line 144 legacy |
| 9.8 | Test visual rendering | Not Started | - | Verify styles work |

## Verification Criteria

✅ No inline style attributes remain
✅ All styles in external CSS files
✅ Vendor prefixes in correct order
✅ apple-touch-icon in <head>
✅ No deprecated CSS properties
✅ Visual appearance unchanged
✅ Linter errors resolved
✅ Both modern and legacy UIs render correctly

## Related Files

- `app/templates/index.html` (modern UI)
- `app/templates/legacy/index.html` (iPad 2 UI)
- `app/static/css/` (new CSS files)
- No test changes needed (visual testing only)

## Notes

Low priority - fixes code quality/linting rather than functionality. Can be tackled after high-priority items.

# TASK005 - Add file extension validation to image uploads

**Status:** Completed
**Priority:** Medium
**Added:** February 10, 2026
**Updated:** February 10, 2026

## Original Request

The `GalleryManager.save_upload()` method in `app/services/image_service.py` processes uploaded files without validating the file extension. While Pillow may throw exceptions, validation should happen before processing.

## Thought Process

Without explicit validation:

- Invalid file types silently processed (user confusion)
- Wasted processing on unsupported formats
- No clear error message to user
- Could accept files with double extensions or spoofed types

Validation should be done early in the upload handler, providing clear feedback. Supported formats are:

- JPEG, JPG
- PNG
- HEIF, HEIC (converted to JPEG)

## Implementation Plan

- [ ] Define ALLOWED_EXTENSIONS constant in image_service.py
- [ ] Add validation in save_upload() before processing
- [ ] Raise ValueError with clear message for invalid types
- [ ] Update admin.py upload_file() to catch and handle validation error
- [ ] Return user-friendly error message in response
- [ ] Add test cases for various file extensions
- [ ] Test valid and invalid extensions

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks

| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 5.1 | Define ALLOWED_EXTENSIONS constant | Completed | February 10, 2026 | Added to app/services/image_service.py |
| 5.2 | Add validation to save_upload() | Completed | February 10, 2026 | Validates extension before processing |
| 5.3 | Raise ValueError with clear message | Completed | February 10, 2026 | Error contains allowed extensions |
| 5.4 | Update admin upload_file() error handling | Completed | February 10, 2026 | Returns gallery partial with error message |
| 5.5 | Return user-friendly HTML error | Completed | February 10, 2026 | Displayed in gallery partial via `error_message` |
| 5.6 | Test valid extension .jpg | Completed | February 10, 2026 | Covered in tests/test_image_service.py |
| 5.7 | Test invalid extension .pdf | Completed | February 10, 2026 | Added test to assert ValueError raised |
| 5.8 | Test case sensitivity .JPG | Completed | February 10, 2026 | Added test for uppercase extension acceptance |

## Progress Log

### February 10, 2026

- Added `ALLOWED_EXTENSIONS` and early extension validation to `GalleryManager.save_upload()`.
- Updated `admin.upload_photos` to catch `ValueError` and render `partials/gallery.html` with a friendly error message.
- Added tests for invalid and uppercase extensions and ran the suite; all tests pass.

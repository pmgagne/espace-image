# TASK005 - Add file extension validation to image uploads

**Status:** Pending
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

**Overall Status:** Not Started - 0%

### Subtasks

| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 5.1 | Define ALLOWED_EXTENSIONS constant | Not Started | - | At module level |
| 5.2 | Add validation to save_upload() | Not Started | - | Before Image.open() |
| 5.3 | Raise ValueError with clear message | Not Started | - | e.g., "File type .pdf not allowed" |
| 5.4 | Update admin upload_file() error handling | Not Started | - | Catch ValueError |
| 5.5 | Return user-friendly HTML error | Not Started | - | In upload response |
| 5.6 | Test valid extension .jpg | Not Started | - | Should succeed |
| 5.7 | Test invalid extension .pdf | Not Started | - | Should return error |
| 5.8 | Test case sensitivity .JPG | Not Started | - | Should be case-insensitive |

## Verification Criteria

✅ Only JPEG, PNG, HEIF files accepted
✅ Invalid extensions rejected with clear error message
✅ Validation happens before file processing (early)
✅ Extension check is case-insensitive
✅ Error message returned to admin UI
✅ Tests cover valid and invalid extensions
✅ User sees friendly error, not exception traceback

## Code Example

```python
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.heif'}

def save_upload(self, file_content: bytes, filename: str, preset_name: str = "Default") -> tuple[Path, str]:
    # Validate extension
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File type {ext} not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}")

    # ... rest of processing
```

## Related Files

- `app/services/image_service.py::GalleryManager.save_upload()` (lines 81-91)
- `app/routers/admin.py::upload_file()` (add error handling)
- `tests/test_image_service.py` (add validation tests)

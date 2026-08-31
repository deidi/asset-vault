# Task 004: Asset Upload & Auto-Tagging System

## Goal
Implement asset upload layer and auto-tagging policies.

## Requirements
- Multipart upload
- UUID filename mapping
- Metadata extraction
- SHA256 hashing
- Database insert & storage
- Automatic tag assignment (complete filename, filetype, current year)
- System protected tag policy (`is_protected_tag`)

## Acceptance
- Asset visible in database after upload with complete filename, filetype extension, and current year tags applied.

---

## 💎 Completion & Verification Status

### Status: COMPLETED

1. **Multipart upload**: Added support for `multipart/form-data` uploads inside `backend/app/routes/asset_routes.py`. The endpoint dynamically detects standard JSON parameters or binary Form fields.
2. **UUID filename**: Generated random UUIDs via python's `uuid.uuid4` to rename stored files on disk, ensuring user file safety (satisfies the constraint to never store user filenames as disk filenames).
3. **Metadata extraction**: Extracted file content type headers and length parameter variables. Integrated the **Pillow** image package to extract pixel dimensions (`width x height`) for image uploads.
4. **SHA256**: Hashed binary file inputs using python's `hashlib.sha256()`.
5. **Automatic upload tagging**: Configured `upload_asset` and `upload_multipart_file` in `AssetService` to auto-tag:
   - **Complete filename** (e.g. `#report.pdf`) — protected system tag.
   - **Filetype extension** (e.g. `#pdf`) — protected system tag.
   - **Current upload year** (e.g. `#2026`).
6. **Protected system tag policy**: Implemented `is_protected_tag()` to prevent direct deletion or replacement of complete filename and filetype system tags, rendering a lock icon (`🔒`) in the UI.
7. **Store file**: Stored physical binary files inside `d:\Projects\AssetVault\storage\`.

### Verification Metrics
- File uploads hash, rename, save, and auto-tag complete filename, filetype extension, and current year.
- Integration tests ran and successfully passed.

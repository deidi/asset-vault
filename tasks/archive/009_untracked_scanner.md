# Task 009: Untracked Files Scanner & Utilities

## Goal
Implement untracked files scanner utility in UI and as a standalone CLI batch script.

## Requirements
- Scan and import UI endpoint (`POST /api/assets/scan-import`)
- Standalone CLI script `scan_untracked.py`
- Batch file launcher `Scan Untracked Files.bat`

## Acceptance
- Files placed manually into `/storage` are detected and registered into SQLite.

---

## 💎 Completion & Verification Status

### Status: COMPLETED

1. **UI Endpoint**: Implemented `scan_and_import_untracked_files` in `AssetService` scanning `/storage` for unregistered files.
2. **Standalone Script**: Built `scan_untracked.py` using direct SQLAlchemy database access to scan `/storage` without requiring FastAPI web server to be running.
3. **One-Click Batch**: Created `Scan Untracked Files.bat` wrapper.

### Verification Metrics
- Unregistered storage files are detected, hashed, assigned UUIDs, auto-tagged, and registered.

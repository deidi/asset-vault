# AssetVault - Testing Strategy & Test Plan

This document outlines the testing strategy, test coverage, and execution instructions for the AssetVault local-first desktop application.

---

## 🎯 Testing Objectives

1. **Integrity & Business Rule Enforcement**: Ensure business logic in services (`AssetService`, `TagService`, `FolderService`, `ExplorerService`) enforces system rules:
   - **In-Place Multi-Folder Ingestion**: Accurately scan and index supported media types (images, videos, audio, PDFs) while ignoring non-media files.
   - **Auto-Tagging Pipeline**: Automatically tag filetype extension (`#ext`), complete filename (`#filename`), year (`#year`), parent folder (`#folder`), and configured custom tags.
   - **Protected System Tags**: System tags matching an asset's complete filename or filetype extension are identified via `is_protected_tag()` and protected from accidental batch overwrites.
   - **Explorer & Shell Operations**: Safely rename files in-place on disk with tag sync; safely send files to Windows Recycle Bin via `send2trash`.
2. **API Route Verification**: Ensure thin FastAPI routers correctly parse inputs, return JSON models, handle HTTP status codes, and manage exception states.
3. **Data Integrity & Storage Verification**: Validate backup archive creation (ZIP/CSV), database restoration, and physical file integrity checks.
4. **Frontend & Compilation Safety**: Ensure React TypeScript frontend builds without compilation or typing errors (`tsc -b && vite build`).

---

## 🧪 Test Architecture & Structure

Test files are located in the `tests/` directory:

```
AssetVault/
├── mds/
│   └── testing_plan.md                 # This comprehensive testing plan
└── tests/
    ├── run_tests.py                    # Automated test runner script (23 tests)
    ├── test_asset_service.py           # Unit tests for asset, tags, and file type filters
    ├── test_api_routes.py              # Integration tests for core asset REST routes
    ├── test_folder_and_explorer.py     # Unit tests for folders, tree counts, moves & explorer
    ├── test_folder_and_explorer_api.py # Integration tests for folder & explorer REST routes
    ├── test_thumbnail_and_cache.py     # Thumbnail generator, video & cache API tests
    ├── test_watcher_service.py         # File watcher lifecycle & event simulation tests
    └── test_ws_api.py                  # WebSocket live sync tests
```

---

## 📋 Test Suites & Coverage

### 1. In-Place Folder & Explorer Service Unit Tests (`tests/test_folder_and_explorer.py`)
- **Multi-Folder Registration & Scanning**: Verifies adding library folders, recursive vs flat scanning, media file type filtering, and auto-tag generation (`#png`, `#filename`, `#year`, `#custom_tag`).
- **Selective Internal Folder Exclusion**: Verifies that internal app directories like `.cache/`, `db/`, `storage/`, `node_modules/`, `.git/`, `.venv/` are selectively ignored while root media files scan properly (`test_excluded_paths_and_app_folders`).
- **Idempotent Scanning**: Verifies that re-scanning an already indexed folder updates stats without duplicating records.
- **In-Place Disk Rename**: Verifies atomic `os.replace` rename on disk, database path synchronization, and `#filename` protected tag migration.
- **Batch Move Operations**: Verifies moving multiple files between directories on disk with collision resolution (`test_batch_move_assets`).
- **Recycle Bin Trashing**: Verifies `send2trash` integration and database cleanup.
- **Folder Tree & Subfolder Filtering**: Verifies recursive subfolder asset count calculations and subfolder queries.

### 2. In-Place Folder & Explorer API Tests (`tests/test_folder_and_explorer_api.py`)
- **Folder CRUD Endpoints**: Tests `POST /api/folders`, `GET /api/folders`, `GET /api/folders/{id}`, `PATCH /api/folders/{id}`, and `DELETE /api/folders/{id}`.
- **Folder Scan Endpoint**: Tests `POST /api/folders/{id}/scan` and `POST /api/folders/scan-all`.
- **Explorer API Endpoints**: Tests `POST /api/explorer/rename` and `POST /api/explorer/trash`.

### 3. Core Business Logic & Service Unit Tests (`tests/test_asset_service.py`)
- **Auto-Tagging Policy**: Verifies uploaded assets are auto-tagged with complete filename, filetype extension, and current year.
- **Protected System Tags**: Verifies `is_protected_tag()` identifies complete filename and filetype tags.
- **Batch Tag Operations**: Tests `batch_add_tags`, `batch_remove_tags`, `batch_replace_tag`, and `batch_set_tags`.
- **Inventory Queries & File Type Filters**: Tests pagination, sorting, text search, and multi-tag AND-logic filtering, plus image, video, audio, and document format filtering (`test_inventory_file_type_filtering`).
- **Asset Deletion & Storage Cleanup**: Verifies DB record removal and file cleanup.

### 4. Core API Route Integration Tests (`tests/test_api_routes.py`)
- **Upload Endpoints**: Tests `POST /api/upload` (JSON metadata and multipart upload).
- **Inventory Endpoint & File Type Filtering**: Tests `GET /api/assets` with pagination, sorting, search, tag filters, and `file_type` filtering (`test_get_assets_file_type_filtering`).
- **Integrity Verification**: Tests `GET /api/assets/verify` integrity report output.

### 5. Thumbnail & Cache Tests (`tests/test_thumbnail_and_cache.py`)
- **Image Thumbnail Generation**: Tests WebP image thumbnail generation and dimension preservation.
- **Video Thumbnail Generation**: Tests native Windows Shell video keyframe extraction and play badge overlay.
- **Cache Clearing & Endpoints**: Tests `GET /api/cache/stats`, `POST /api/cache/clear`, and `POST /api/library/rescan`.

### 6. Watcher Service & Live Sync Tests (`tests/test_watcher_service.py`, `tests/test_ws_api.py`)
- **Watcher Lifecycle**: Tests starting, scheduling, unscheduling, and stopping watchdog directory observers.
- **Handler Event Simulation**: Tests simulated `on_created`, `on_moved`, and `on_deleted` filesystem events.
- **WebSocket Broadcast**: Tests WebSocket client connection and ping/pong heartbeat.

---

## 🚀 Running the Tests

### Command Line Execution
Run all 23 unit and integration tests using the Python virtual environment:

```powershell
# From the project root directory
.\backend\.venv\Scripts\python.exe tests/run_tests.py
```

### Expected Output
```text
==================================================
        ASSETVAULT TEST SUITE EXECUTION           
==================================================
...
----------------------------------------------------------------------
Ran 23 tests in 1.350s

OK
==================================================
        ASSETVAULT TEST SUITE EXECUTION           
==================================================

Test Summary:
  Total Run : 23
  Failures  : 0
  Errors    : 0
```

# AssetVault AI Reload & Onboarding Guide

Welcome! This guide provides a rapid reference for bootstrapping your context when reloading or starting a new session on the **AssetVault** repository.

---

## 🏛️ System Architecture & Layout

AssetVault is built with a Clean Architecture structure, overhauled as a **Standalone Windows Desktop Application** with **In-Place Multi-Folder Reference Mode**:

```
d:\Projects\asset-vault/
├── .agents/
│   ├── AGENTS.md                   # Workspace development rules & constraints
│   └── RELOAD.md                   # This onboarding / reload guide
├── backend/
│   ├── app/
│   │   ├── config.py               # Configuration & env setup
│   │   ├── db/                     # SQLAlchemy engine & session setup
│   │   ├── models/                 # SQLAlchemy DB models (Asset, Tag, AssetTag, LibraryFolder)
│   │   ├── repositories/           # DB data access layer (AssetRepo, TagRepo, LibraryFolderRepo)
│   │   ├── routes/                 # Thin FastAPI endpoints (asset, inventory, folder, explorer, thumbnail)
│   │   ├── schemas/                # Pydantic schemas (Asset, Tag, LibraryFolder, Explorer)
│   │   └── services/               # Core business logic (AssetService, TagService, FolderService, ExplorerService, ThumbnailService)
│   ├── db/
│   │   ├── assetvault.sqlite       # Active SQLite database file
│   │   └── settings.json           # Persistent storage & library settings
│   └── requirements.txt            # Python dependencies (FastAPI, SQLAlchemy, Pillow, send2trash, watchdog, pywebview)
├── dist/
│   └── AssetVault.exe              # Self-contained standalone Windows executable
├── docs/                           # API docs, architecture, roadmap, testing plan
├── frontend/
│   ├── src/
│   │   ├── App.tsx                 # Main application containing layout, header, state
│   │   ├── components/             # React UI components (Sidebar, MediaGrid, InspectorPanel, PreviewModal, etc.)
│   │   └── main.tsx                # React client entrypoint with ErrorBoundary
│   └── package.json                # Node.js dependencies & scripts
├── public/                         # Built frontend SPA bundle served by FastAPI & PyWebView
├── storage/                        # Physical file storage directory for internal vault imports
├── tasks/
│   ├── TASKS_SUMMARY.md            # Master task summary index
│   └── archive/                    # Archived historical task logs (000 - 012)
├── tests/                          # 19/19 passing automated test suite
│   ├── run_tests.py                # Automated test runner
│   ├── test_asset_service.py       # AssetService unit tests
│   ├── test_api_routes.py          # REST API integration tests
│   ├── test_folder_and_explorer.py # Folder & Explorer service unit tests
│   ├── test_folder_and_explorer_api.py # Folder & Explorer REST API integration tests
│   ├── test_thumbnail_and_cache.py # Thumbnail generator & video thumbnail tests
│   ├── test_watcher_service.py     # File watcher lifecycle & event tests
│   └── test_ws_api.py              # WebSocket live sync tests
├── build_desktop.py                # Standalone PyInstaller builder
├── desktop_app.py                  # PyWebView desktop launcher entrypoint
└── run_desktop.bat                 # Batch launcher for Windows
```

---

## 💾 Data Models & Key Policies

### 1. Database Entities
- **LibraryFolder** (`app.models.library_folder.LibraryFolder`):
  - `id`: UUID (Primary Key, String)
  - `path`: Absolute disk directory path (unique)
  - `name`: User-facing folder display name
  - `is_recursive`: Boolean (recursive subfolder scan toggle)
  - `auto_tag_folder`: Boolean (parent directory auto-tag toggle)
  - `custom_tags`: Comma-separated list of custom tag strings to auto-apply
  - `is_active`: Boolean (active library folder toggle)
  - `created_at`: Datetime
  - `assets`: One-to-Many relationship with `Asset`
- **Asset** (`app.models.asset.Asset`):
  - `id`: UUID (Primary Key, String)
  - `name`: User-facing asset display name (or filename on disk)
  - `original_name`: Original uploaded or disk filename
  - `mime_type`: Content type (e.g. `image/png`, `video/mp4`, `audio/mp3`, `application/pdf`)
  - `size_bytes`: Integer size of the file
  - `storage_path`: Absolute disk path for in-place files, or relative path for internal vault files
  - `description`: Optional text details
  - `folder_id`: Foreign key to `library_folders.id` (nullable)
  - `file_modified_at`: Timestamp of file on disk
  - `file_hash`: Optional hash for integrity validation
  - `thumbnail_path`: Cached `.webp` thumbnail path
  - `created_at`: Datetime
  - `tags`: Many-to-Many relationship with `Tag`
- **Tag** (`app.models.tag.Tag`):
  - `id`: UUID (Primary Key, String)
  - `name`: Unique tag name string (e.g. `#png`, `#Photos`, `#2026`, `#video.mp4`)
  - `created_at`: Datetime

### 2. In-Place Media & File Explorer Integration
- Media files remain in their original folders on disk.
- **Show in Explorer**: `POST /api/explorer/reveal` launches Windows File Explorer highlighting the exact item (`explorer.exe /select,"<path>"`).
- **In-Place Rename**: `POST /api/explorer/rename` renames the file on disk (`os.replace`) and updates DB records & `#filename` tag atomically.
- **Recycle Bin Trashing**: `POST /api/explorer/trash` safely sends files to the Windows Recycle Bin using `send2trash`.

### 3. Video Thumbnail Generation Policy
- Uses native Windows Shell `IThumbnailProvider` via ctypes (`shell32.dll`, `ole32.dll`) to extract crystal-clear keyframes from `.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`, `.wmv`, `.m4v`, etc.
- Overlays a semi-transparent video play badge in the thumbnail center.
- Optimizes and caches thumbnails as `.webp` files under `.cache/thumbnails/`.

### 4. Ingestion Auto-Tagging Policy
- On folder scanning / indexing, AssetVault automatically assigns:
  - **Filetype extension** (e.g. `#png`, `#mp4`, `#pdf`) — protected system tag.
  - **Complete filename** (e.g. `#banner.png`) — protected system tag.
  - **Current/Modified year** (e.g. `#2026`).
  - **Parent folder name** (e.g. `#Photos`) if `auto_tag_folder` is enabled.
  - **Custom folder rules** (e.g. `#ProjectAlpha`) configured on the library folder.
- Tags matching an asset's complete filename or filetype extension are identified via `is_protected_tag()` as protected system tags (`🔒`).

### 5. Tag Search & Matching Policy
- Frontend strips `#` for clean display chips.
- Backend `AssetService.get_inventory` filters tags via `or_(Tag.name.ilike(clean), Tag.name.ilike(f"#{clean}"))` to seamlessly match both prefixed and non-prefixed records with AND-logic.

### 6. Background Process & Watcher Shutdown Policy
- **FastAPI Lifespan Context**: File watchers (`WatcherService`) start on startup and stop on shutdown.
- **Process Exit (`atexit`) Hooks**: `atexit.register(watcher_service.stop_all)` ensures all watchdog Win32 observer/emitter threads terminate cleanly upon process exit.
- **Desktop Window Closed Hook**: When the PyWebView window closes (`window.events.closed`), the application triggers full graceful shutdown, terminating backend threads and preventing orphaned background processes (Rule #14).

### 7. Standalone Executable Packaging Policy
- **Automatic Portable Executable Rebuild**: Whenever changes are made to frontend assets or backend services, the standalone desktop executable must be repackaged via `python build_desktop.py` to ensure `dist/AssetVault.exe` is kept synchronized (Rule #15).

---

## 🚀 Quick Execution Commands

### 1. Run Desktop Application
```powershell
.\run_desktop.bat
```

### 2. Build Standalone Desktop Executable
```powershell
.\backend\.venv\Scripts\python.exe build_desktop.py
```

### 3. Run Automated Backend Test Suite
```powershell
.\backend\.venv\Scripts\python.exe tests/run_tests.py
```

### 4. Build Frontend Bundle
```powershell
cd frontend; npm.cmd run build; cd ..
```

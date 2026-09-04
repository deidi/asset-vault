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
├── docs/                           # GitHub Pages static site & SEO assets
│   ├── index.html                  # Landing page
│   ├── favicon.png                 # Multi-resolution favicon & app icons
│   ├── og-preview.jpg              # High-res social preview card
│   ├── robots.txt                  # Search engine directives
│   └── sitemap.xml                 # XML sitemap for search indexing
├── frontend/
│   ├── src/
│   │   ├── App.tsx                 # Main application containing layout, header, state
│   │   ├── components/             # React UI components (Sidebar, MediaGrid, InspectorPanel, PreviewModal, etc.)
│   │   └── main.tsx                # React client entrypoint with ErrorBoundary
│   └── package.json                # Node.js dependencies & scripts
├── mds/                            # Technical & system documentation
│   ├── api.md                      # REST API specification
│   ├── architecture.md             # System architecture & Clean Architecture layers
│   ├── privacy_policy.md           # Privacy policy & offline assurance
│   ├── roadmap.md                  # Milestone roadmap & slice progress
│   └── testing_plan.md             # Testing strategy and automated test suites
├── public/                         # Built frontend SPA bundle served by FastAPI & PyWebView
├── storage/                        # Physical file storage directory for internal vault imports
├── tasks/
│   ├── TASKS_SUMMARY.md            # Master task summary index
│   └── archive/                    # Archived historical task logs (000 - 012)
├── tests/                          # 23/23 passing automated test suite
│   ├── run_tests.py                # Automated test runner (23 tests)
│   ├── test_asset_service.py       # AssetService & file type filter unit tests
│   ├── test_api_routes.py          # REST API & file type integration tests
│   ├── test_folder_and_explorer.py # Folder, tree counts, batch move & explorer unit tests
│   ├── test_folder_and_explorer_api.py # Folder & Explorer REST API integration tests
│   ├── test_thumbnail_and_cache.py # Thumbnail generator & video thumbnail tests
│   ├── test_watcher_service.py     # File watcher lifecycle & event tests
│   └── test_ws_api.py              # WebSocket live sync tests
├── version_info.txt                # Windows File Version metadata resource
├── build_desktop.py                # Standalone PyInstaller builder
├── desktop_app.py                  # PyWebView desktop launcher entrypoint
└── run_desktop.bat                 # Batch launcher for Windows
```

---

## 💾 Data Models & Key Policies

### 1. Database Entities & Concurrency
- **SQLite WAL Mode**: Configured with `PRAGMA journal_mode=WAL;` and 30-second busy timeout in `backend/app/db/session.py` to prevent locking between the FastAPI request thread pool and Watchdog observer threads.
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
- **Batch Move**: `POST /api/explorer/batch-move` moves files to destination folder with quote stripping (Windows "Copy as path"), collision resolution (`file_1.ext`), and watcher suppression.
- **Recycle Bin Trashing**: `POST /api/explorer/trash` safely sends files to the Windows Recycle Bin using `send2trash`.

### 3. Watcher Event Suppression Policy
- During internal move/rename/trash operations in `ExplorerService`, paths are registered in `watcher_service.suppress_paths()`.
- Watchdog handlers (`on_deleted`, `on_created`, `on_moved`) check `is_suppressed()` to avoid deleting or modifying database rows before the main API transaction commits.

### 4. Dynamic Catalog Sizing & Select All
- Frontend computes `pageSize: Math.max(1000, allAssetsCount)` using the sum of asset counts from all registered libraries.
- Backend `get_inventory` supports unconstrained loading without hardcoded caps when requesting full libraries.
- Global `Ctrl + A` (and `Cmd + A`) selects all assets across the entire library at once.

### 5. Ingestion Auto-Tagging & File Type Filtering
- On folder scanning / indexing, AssetVault automatically assigns:
  - **Filetype extension** (e.g. `#png`, `#mp4`, `#pdf`) — protected system tag.
  - **Complete filename** (e.g. `#banner.png`) — protected system tag.
  - **Current/Modified year** (e.g. `#2026`).
  - **Parent folder name** (e.g. `#Photos`) if `auto_tag_folder` is enabled.
  - **Custom folder rules** (e.g. `#ProjectAlpha`) configured on the library folder.
- Assets are categorizable via `file_type` query filter (`image`, `video`, `audio`, `document`, `all`).

### 6. Background Process & Watcher Shutdown Policy
- **FastAPI Lifespan Context**: File watchers (`WatcherService`) start on startup (with background startup sync of offline files) and stop on shutdown.
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

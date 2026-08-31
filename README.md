# 🏛️ AssetVault

AssetVault is a production-quality, local-first asset management system overhauled as a **Standalone Windows Desktop Application** with an **In-Place Multi-Folder Reference Engine**.

Original media files remain directly in your selected folders on disk. AssetVault provides instant indexing, real-time background file watching (`watchdog`), cached WebP thumbnail generation, rich media previewers (Images, Videos, Audio, PDFs), a collapsible Inspector panel with native Windows File Explorer integration, and flexible bulk management operations.

---

## 🚀 Features

- **In-Place Multi-Folder Library**: Select one or multiple media folders on your computer. Files remain directly in place on your disk while AssetVault indexes and tags them.
- **Recursive & Flat Folder Scanning**: Toggle between recursive subfolder scanning or top-level scanning for each configured folder.
- **Supported Media Bundle**: Indexes and previews Images (`png, jpg, jpeg, gif, webp, svg, bmp`), Videos (`mp4, webm, mov, mkv, avi`), Audio (`mp3, wav, ogg, flac`), and PDFs.
- **Native File Explorer Actions**:
  - **Show in Explorer**: Instantly reveal and select the exact file in Windows File Explorer (`explorer.exe /select`).
  - **In-Place Rename**: Safely rename files on disk (`os.replace`) with automatic database metadata and tag synchronization.
  - **Recycle Bin Trashing**: Safely send deleted files to the Windows Recycle Bin using `send2trash`.
- **Granular Auto-Tagging Engine**:
  - Automatically tags filetype extension (e.g., `#png`, `#pdf`) and complete filename (e.g., `#photo.jpg`) as protected system tags (`🔒`).
  - Automatically tags creation/modified year (e.g., `#2026`).
  - Configurable toggle for parent folder name auto-tagging (e.g., `#Photos`).
  - Custom folder-level tag presets (e.g., `#ProjectAlpha`).
- **Inventory Dashboard & Multi-Tag Search**: Full-text searching, pagination, sorting (date, name, size), and **AND-logic multi-tag filtering**.
- **Batch Management Operations**: Multi-select assets (with `Shift`/`Ctrl`-click and page selection) to batch add/remove/replace tags, batch rename, batch move to directory, and batch trash.
- **Real-Time Watcher**: Background `watchdog` Win32 kernel hooks auto-reconcile external additions, renames, and deletions in real time with WebSocket sync (`/api/ws/events`).
- **High-Performance WebP Thumbnail Cache**: On-demand WebP generation for images, PDFs (`pypdfium2`), videos, and audio with diagnostic cache clearance and rescan tools.
- **Collapsible Inspector Panel**: Right-hand drawer with in-place rename, reveal in Explorer, send to Recycle Bin, metadata, and tag manager with protected system tag indicators (`🔒`).
- **Rich Media Previewers**: Full-screen interactive modal with image zoom/pan/rotate, HTML5 video player with speed controls, waveform audio player, vector PDF viewer, and keyboard shortcuts (`Arrows`, `Esc`).
- **Standalone Desktop Executable**: Native desktop window powered by PyWebView and PyInstaller with clean window shutdown hooks (`window.events.closed` + `atexit`).

---

## 🛠️ Technology Stack

| Layer       | Technology                                                                 |
|-------------|----------------------------------------------------------------------------|
| Shell       | PyWebView (Native Windows Application Window) + PyInstaller               |
| Frontend    | React 19 + TypeScript + Vite + TailwindCSS + Lucide Icons                  |
| Backend     | FastAPI + Uvicorn (Python 3.10+)                                           |
| Database    | SQLite via SQLAlchemy ORM (Clean Architecture)                             |
| File System | In-Place reference mode, `watchdog` Win32 events, `send2trash` Recycle Bin |
| Media       | Pillow (PIL) + WebP thumbnail cache generator                              |

---

## 📁 Repository Structure

```
d:\Projects\asset-vault/
├── .agents/                    # AI Agent development rules & onboarding
│   ├── AGENTS.md               # Architecture rules & constraints
│   └── RELOAD.md               # Quick start onboarding reference
├── backend/                    # FastAPI Clean Architecture backend
│   ├── app/
│   │   ├── config.py           # Configuration & environment variables
│   │   ├── db/                 # Database engine & SQLite session
│   │   ├── models/             # SQLAlchemy DB models (Asset, Tag, LibraryFolder)
│   │   ├── repositories/       # Data access query layers
│   │   ├── routes/             # Thin FastAPI REST routers
│   │   ├── schemas/            # Pydantic input/output validation schemas
│   │   └── services/           # Business logic (Folder, Explorer, Asset, Tag)
│   └── requirements.txt        # Python dependencies
├── docs/                       # System documentation
│   ├── api.md                  # REST API specification
│   ├── architecture.md         # System architecture & Clean Architecture layers
│   ├── roadmap.md              # Milestone roadmap & 6-slice overhaul plan
│   └── testing_plan.md         # Testing strategy and automated test suites
├── frontend/                   # React + TypeScript SPA client
│   ├── src/                    # Components, pages, hooks, state
│   ├── package.json            # Node.js dependencies
│   └── vite.config.ts          # Vite build config
├── public/                     # Compiled frontend bundle served by FastAPI & PyWebView
├── storage/                    # Storage directory for internal vault imports
├── tasks/                      # Milestone documentation
│   ├── TASKS_SUMMARY.md        # Master task summary index
│   └── archive/                # Historical task logs (000 - 012)
└── tests/                      # Automated test suite
    ├── run_tests.py            # Test runner
    ├── test_asset_service.py   # Asset & tag logic unit tests
    ├── test_api_routes.py      # Core asset REST route tests
    ├── test_folder_and_explorer.py     # In-place folder & explorer unit tests
    └── test_folder_and_explorer_api.py # In-place folder & explorer API tests
```

---

## 🚀 Running the Application & Tests

### 1. Run Standalone Desktop Application
```powershell
# Launch native PyWebView desktop window
.\run_desktop.bat

# Or run with python directly
.\backend\.venv\Scripts\python.exe desktop_app.py
```

### 2. Build Standalone Desktop Executable
```powershell
# Automates frontend build, test verification, and PyInstaller bundling
.\backend\.venv\Scripts\python.exe build_desktop.py
```

### 3. Run Automated Backend Test Suite
```powershell
.\backend\.venv\Scripts\python.exe tests/run_tests.py
```

### 4. Start as Local Web Server
```powershell
# Using PowerShell launcher
powershell -NoProfile -ExecutionPolicy Bypass -File .\assetvault_start.ps1

# Or run FastAPI directly
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

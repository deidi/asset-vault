# 🏛️ AssetVault

[![AssetVault CI & Build](https://github.com/deidi/asset-vault/actions/workflows/ci.yml/badge.svg)](https://github.com/deidi/asset-vault/actions/workflows/ci.yml)
![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-blue)
![Architecture](https://img.shields.io/badge/architecture-Local--First%20%7C%20In--Place-emerald)
![License](https://img.shields.io/badge/license-MIT-purple)

AssetVault is a production-quality, local-first asset management system built as a **Standalone Windows Desktop Application** with an **In-Place Multi-Folder Reference Engine**.

Original media files remain directly in their selected folders on disk. AssetVault provides instant indexing, real-time background file watching (`watchdog`), cached WebP thumbnail generation, rich media previewers (Images, Videos, Audio, PDFs), a collapsible Inspector panel with native Windows File Explorer integration, and flexible bulk management operations.

---

## 📖 First-Time User Guide: How to Use AssetVault

Welcome to AssetVault! Here is a step-by-step walkthrough to get you started immediately:

### 1. 🚀 Launching AssetVault
* **Option A (Portable Executable)**: Double-click `dist\AssetVault.exe`. No installation, Python, or Node.js required.
* **Option B (Launcher Script)**: Double-click `run_desktop.bat` in the project root.
* **Option C (Development Mode)**: Run `.\backend\.venv\Scripts\python.exe desktop_app.py`.

---

### 2. 📁 Adding Your First Library Folder
1. When AssetVault opens, click the **`+ Add Folder`** button in the left sidebar (or click the plus icon beside *Library Folders*).
2. Click **Browse...** to select any folder on your computer containing your photos, videos, audio, or documents.
3. Configure your preferences:
   * **Include subfolders recursively**: Keep checked to scan all nested folders inside.
   * **Auto-tag folder name**: Automatically applies the parent folder name as a tag (e.g. `#Media`).
   * **Custom Tags**: Add any initial tags you'd like applied to files in this folder.
4. Click **Add & Index Folder**. AssetVault will immediately scan the folder, index its contents, and generate thumbnails.

---

### 3. 🌳 Navigating Folders & Subfolder Trees
* **All Assets Library**: Click the top item in the sidebar to see all indexed media across all your registered library folders (with total vault count badge).
* **Parent Folders**: Click on any registered library folder to filter assets strictly to that folder.
* **Subfolder Tree**: Click the arrow (`›` / `⌄`) next to any folder with subdirectories to expand the hierarchical subfolder tree. Clicking any nested subfolder will instantly filter the media grid to that exact path.
* **Asset Count Badges**: Every parent folder and subfolder branch displays its exact real-time asset count badge.

---

### 4. 🔍 Searching, File Type & Tag Filtering
* **Dynamic Search Bar**: Type in the top search bar to search across filenames, descriptions, and tags. The search bar dynamically adapts when the window is resized.
* **File Type Filters**: Use the format filter pills sub-bar to instantly filter your grid by **All Files**, **Images** (`ImageIcon`), **Videos** (`Film`), **Audio** (`Music`), or **Documents** (`FileText`).
* **Tag Chips**: In the sidebar's **Tags** section, click on any tag chip (e.g., `#mp4`, `#2026`, `#Audio`) to filter your media.
* **Multi-Tag AND-Logic**: Click multiple tags to combine them. AssetVault filters to assets containing *all* selected tags.
* **Clear Filters**: Click *Clear all* or the empty state reset buttons to instantly reset tag and file type filters.

---

### 5. 🎬 Viewing & Playing Media
* **Media Grid**: Scroll through responsive cards displaying generated WebP thumbnails. Video files feature extracted frame previews with centered play overlays.
* **Full-Screen Previewer**: Double-click any card (or select it and press `Enter` / click the expand icon) to open the high-definition preview modal:
  * **Images**: Zoom, pan, rotate, and view dimensions.
  * **Videos**: Built-in HTML5 video player with playback speeds, volume slider, fullscreen, and seekbar.
  * **Audio**: Waveform audio player with playback controls.
  * **PDFs**: Vector page renderer.
  * **Keyboard Navigation**: Use Left/Right Arrow keys to jump to the previous/next asset, and `Esc` to close.

---

### 6. 🛠️ Using the Inspector Panel
Click once on any media card to open the right-hand Inspector drawer:
* **In-Place Disk Rename**: Click the pencil icon next to the filename, type a new name, and press `Enter`. AssetVault safely renames the file directly on your hard drive (`os.replace`) and updates the `#filename` tag automatically.
* **Reveal in Explorer**: Click **Show in Explorer** to immediately highlight the exact file in Windows File Explorer (`explorer.exe /select`).
* **Move to Another Folder**: Click **Move to Another Folder** to browse or enter a destination directory on disk and move the file safely with watcher suppression.
* **Tag Management**: Add new tags or remove existing ones with individual `✕` buttons. System tags (file extension and complete filename) are safely marked with a `🔒` protected lock badge.
* **Send to Recycle Bin**: Click **Move to Recycle Bin** to safely send the file on disk to the Windows Recycle Bin (`send2trash`).

---

### 7. 📦 Multi-Select & Batch Operations
* **Select All (`Ctrl + A` / `Cmd + A`)**: Press `Ctrl + A` (or `Cmd + A` on macOS) anywhere on the grid or click the top toolbar checkbox to select all assets across the entire library at once (without 500-item caps). Press `Esc` to deselect all.
* **Multi-Select**: Hold `Ctrl` (or `Cmd`) while clicking cards to select multiple items, or hold `Shift` to select a range.
* **Batch Action Bar**: When multiple items are selected, a floating toolbar appears at the bottom allowing you to:
  * **Batch Add Tags**: Apply one or more tags across all selected assets at once.
  * **Batch Remove Common Tags**: View all shared tags across the selected assets and click individual `✕` chips or "Remove All Common Tags" to strip them cleanly.
  * **Batch Move**: Relocate all selected files on disk to a target directory with native Windows folder browsing, automatic quote sanitization (for Windows "Copy as path"), and collision resolution (`file_1.ext`).
  * **Batch Recycle Bin**: Safely send all selected files to the Windows Recycle Bin.
  * **Download ZIP**: Package selected files into a single ZIP archive.

---

### 8. ⚡ Cache Management & Live File System Sync
* **Live Sync & Startup Reconcile**: On launch, AssetVault automatically scans all registered library folders in the background, indexing any files created while the app was closed and pre-generating WebP thumbnails.
* **Real-Time Watcher**: The green indicator in the sidebar confirms that the background file watcher (`watchdog`) is active with thread-safe event suppression (`suppress_paths`).
* **Cache Manager**: Click the database settings icon at the bottom of the sidebar to view thumbnail disk usage, flush cached WebP thumbnails, or trigger a full library integrity rescan.

---

## 🚀 Key Features Summary

- **In-Place Reference Mode**: Zero duplicate files — media stays on your hard drive.
- **Dynamic Library Catalog Sizing**: Automatically sizes catalog requests based on total active library file counts for seamless full-library browsing and `Ctrl + A` selection.
- **File Type Filters**: Dedicated format sub-bar for Images, Videos, Audio, Documents, and All files.
- **Recursive Subfolder Tree**: Collapsible tree with O(1) cached branch count calculations.
- **Video Keyframe Thumbnail Generator**: Native Windows Shell frame extraction with zero external dependencies.
- **Real-Time Watcher & Event Suppression**: Background Win32 kernel hooks auto-reconcile file system changes via WebSockets while suppressing internal move/rename events to prevent race conditions.
- **Protected System Tags & Common Tag Chips**: Distinguishes auto-generated tags (`🔒`) and displays common tags with individual removal chips.
- **Recycle Bin Integration**: Full `send2trash` integration for non-destructive trashing.
- **Modern Dark UI**: Glassmorphism aesthetic, tailored color palette, responsive search bar, and custom slim scrollbars.
- **Standalone Desktop Distribution**: Self-contained single executable (`AssetVault.exe`) packaged with PyInstaller and PyWebView.

---

## 🛠️ Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Desktop Shell** | PyWebView + PyInstaller (Standalone `.exe`) |
| **Frontend** | React 19 + TypeScript + Vite + TailwindCSS + Lucide Icons |
| **Backend** | FastAPI + Uvicorn (Python 3.10+) |
| **Database** | SQLite with WAL mode & 30s busy timeout via SQLAlchemy ORM |
| **File System** | In-Place reference mode, `watchdog` Win32 events with event suppression, `send2trash` Recycle Bin |
| **Media & Video** | Windows Shell `IThumbnailProvider` + Pillow (PIL) WebP Cache |

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
│   │   ├── db/                 # Database engine & SQLite session (WAL mode)
│   │   ├── models/             # SQLAlchemy DB models (Asset, Tag, LibraryFolder)
│   │   ├── repositories/       # Data access query layers
│   │   ├── routes/             # Thin FastAPI REST routers
│   │   ├── schemas/            # Pydantic input/output validation schemas
│   │   └── services/           # Business logic (Folder, Explorer, Asset, Tag, Thumbnail, Watcher)
│   ├── db/                     # SQLite database files
│   └── requirements.txt        # Python dependencies
├── dist/                       # Standalone application build output
│   └── AssetVault.exe          # Portable Windows desktop executable (39.2 MB)
├── docs/                       # System documentation
│   ├── api.md                  # REST API specification
│   ├── architecture.md         # System architecture & Clean Architecture layers
│   ├── roadmap.md              # Milestone roadmap
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
├── tests/                      # Automated test suite (22/22 tests passing)
│   ├── run_tests.py            # Test runner (22 tests)
│   ├── test_asset_service.py   # Asset & tag logic unit tests
│   ├── test_api_routes.py      # Core asset REST route tests
│   ├── test_folder_and_explorer.py     # In-place folder & explorer unit tests
│   ├── test_folder_and_explorer_api.py # In-place folder & explorer API tests
│   ├── test_thumbnail_and_cache.py     # Thumbnail generator & video test
│   ├── test_watcher_service.py         # File watcher lifecycle tests
│   └── test_ws_api.py                  # WebSocket live sync tests
├── build_desktop.py            # Automated desktop application packager
├── desktop_app.py              # PyWebView desktop launcher entrypoint
└── run_desktop.bat             # Batch launcher for Windows
```

---

## 💻 Development & Build Commands

### 1. Run the Desktop Application
```powershell
.\run_desktop.bat
# Or:
.\backend\.venv\Scripts\python.exe desktop_app.py
```

### 2. Build the Standalone Executable
```powershell
.\backend\.venv\Scripts\python.exe build_desktop.py
```
*Outputs self-contained binary at `dist\AssetVault.exe`.*

### 3. Run Automated Tests
```powershell
.\backend\.venv\Scripts\python.exe tests/run_tests.py
```

### 4. Build Frontend Bundle
```powershell
cd frontend
npm.cmd run build
```

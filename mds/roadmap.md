# AssetVault - Project Roadmap

This document outlines the milestones and release plan for the AssetVault local-first asset management system and its standalone desktop application overhaul.

---

## 🏁 Milestone 1: Release v1.0.0 (Production Core & LAN Management Suite) - COMPLETED
- Local-first SQLite Database & Clean Architecture layout.
- FastAPI REST endpoints for inventory search, AND-logic tag filtering, upload dropzone, and asset details.
- Automatic upload tagging: complete filename (`#filename`), filetype extension (`#ext`), and current year (`#2026`).
- Batch tag operations (Add, Remove, Replace, Set) with protected system tag preservation.
- Physical ZIP download bundling, CSV/ZIP backup and restore, and storage integrity verification.
- Packaging & Standalone Installers: NSIS Setup executable (`AssetVault_Setup.exe`), scripted ZIP installer, and zero-install portable package.

---

## 🚀 Milestone 2: Release v2.0.0 (Standalone Desktop Application Overhaul) - COMPLETED

The overhaul has transformed AssetVault into a **high-performance standalone Windows Desktop Application (`.exe`)** powered by **PyWebView + PyInstaller** and an **In-Place Multi-Folder Reference Engine**.

### 6-Slice Phased Implementation Roadmap:

#### ✅ **Slice 1: Database Schema & In-Place Multi-Folder Core Backend (COMPLETED)**
- `LibraryFolder` model and `Asset` in-place storage paths.
- `FolderService` for folder registration, recursive/flat scanning, media filtering (images, videos, audio, PDFs), and auto-tagging.
- `ExplorerService` for Windows File Explorer reveal (`explorer.exe /select`), atomic in-place rename, and Recycle Bin trashing (`send2trash`).
- `/api/folders` and `/api/explorer` REST routes with 100% test coverage.

#### ✅ **Slice 2: Real-Time Background File Watcher & WebSocket Sync (COMPLETED)**
- `watchdog` integration tracking active library folders via Win32 `ReadDirectoryChangesW` kernel hooks.
- Auto-reconcile engine: dynamically updates DB on external file drops, renames, and deletions.
- WebSocket broadcast endpoint (`/api/ws/events`) for live UI synchronization.

#### ✅ **Slice 3: Thumbnail Generation Engine & Cache Management (COMPLETED)**
- High-performance WebP thumbnail generator for images (Pillow), video frames, audio waveforms, and PDF first pages (`pypdfium2`).
- Lazy-loading thumbnail serving endpoint (`GET /api/assets/{id}/thumbnail`).
- Cache maintenance tools: Clear thumbnail cache (`POST /api/cache/clear`) and full library re-scan (`POST /api/library/rescan`).

#### ✅ **Slice 4: Frontend Multi-Folder Library, Virtual Grid & Bulk Actions (COMPLETED)**
- Library folder manager sidebar with add/edit/rescan folder modals and recursive scan toggle.
- Responsive media grid with Shift/Ctrl multi-selection matrix and Select All.
- Floating Bulk Action Toolbar: Batch tagging, batch move, and batch recycle bin trashing.

#### ✅ **Slice 5: Collapsible Inspector Panel & Rich Media Previewers (COMPLETED)**
- Collapsible right-hand inspector panel with metadata, tags, action buttons ("Show in Explorer", "Rename", "Trash"), and mini preview pane.
- Full-Screen Interactive Preview Modal (double-click trigger):
  - Images: Zoom in/out, pan, 90° rotate, reset view.
  - Videos: HTML5 player with speed controls (0.5x - 2x) and scrub bar.
  - Audio: Audio player with volume and waveform badge.
  - PDFs: Vector-embedded document reader.
  - Keyboard navigation: Left/Right arrows and Escape to close.

#### ✅ **Slice 6: Desktop Executable Packaging (PyWebView + PyInstaller) (COMPLETED)**
- Standalone native Windows application entrypoint ([desktop_app.py](file:///d:/Projects/asset-vault/desktop_app.py)) with PyWebView window controls.
- Clean process shutdown hooks (`window.events.closed` + `atexit.register(watcher_service.stop_all)`) preventing orphaned processes.
- PyInstaller spec ([assetvault.spec](file:///d:/Projects/asset-vault/assetvault.spec)) and automated desktop build script ([build_desktop.py](file:///d:/Projects/asset-vault/build_desktop.py)).

---

## 🚀 Milestone 2.1: Release v1.0 & v1.0.2 (Advanced UX & File Management Suite) - COMPLETED
- **File Type Format Filters**: Filter media grid by All, Images, Videos, Audio, or Documents.
- **Dynamic Catalog Sizing & Select All**: Global `Ctrl + A` / `Cmd + A` selecting thousands of assets seamlessly without hardcoded limits.
- **Watchdog Event Suppression & SQLite WAL Concurrency**: Thread-safe event suppression preventing `StaleDataError` race conditions during batch moves, renames, and trashing.
- **Common Tags Redesign**: Visual chip-based removal for shared tags across selected assets.
- **Startup Library Reconcile**: Background sync scanning and indexing newly added offline files on app launch.
- **GitHub Release CI/CD**: Automated GitHub Action publishing `dist/AssetVault.exe` to GitHub Releases on tag push (`v*`).

---

## 🔮 Milestone 3: Future Enhancements (v1.2.0+)
- AI-based local semantic tagging (CLIP/BLIP local vision models running offline on ONNX/DirectML).
- Duplicate and near-duplicate visual media detection (perceptual hashing).
- EXIF GPS geotagging & interactive offline map explorer.

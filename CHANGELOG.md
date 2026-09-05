# Changelog

All notable changes to **AssetVault** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2026-09-05

### Added
- **Dedicated "Other Files" Tab**: Full support for non-media asset formats (`.zip`, `.blend`, `.exe`, `.py`, `.iso`, `.json`, `.obj`, `.csv`, `.fbx`, `.ttf`, etc.) accessible via a dedicated Amber "Other Files" tab in the header.
- **Media Isolation**: The primary "All Files" tab strictly filters for visual and audio media (`image`, `video`, `audio`, `document`), ensuring archives and scripts never clutter the media gallery.
- **Dynamic Format Badges**: Generates dark-slate uppercase format badge thumbnails for non-media files (`ZIP`, `BLEND`, `EXE`, `PY`, etc.) with packaging format icons.
- **Smart Move Reconciliation**: Scanner and live watchers automatically detect files moved or renamed externally outside the app by matching `(name, size_bytes)` in-place, updating paths without losing custom tags, UUIDs, or metadata.
- **Automatic Orphan Purging**: Missing or externally deleted library records are cleanly removed from the database during folder scans (`orphans_purged`).
- **User-Configurable Category File Types**: Ability to manually customize and add file extension mappings for each filtering category (**Documents**, **Images**, **Videos**, and **Audio**) in case an associated format is missed (e.g. `.heic`, `.raw`, `.mkv`, `.epub`). Includes a dedicated settings modal with chip tags, instant collision auto-transfer, and automated live re-classification of existing library assets.
- **Database Index Architecture**: Added B-Tree indexes on `storage_path`, `folder_id`, `category`, `created_at`, `name`, and `mime_type` with auto-migration and startup backfill.

### Performance & Optimizations
- **Ultra-Fast Library Scanner (9,000+ Assets in Seconds)**: Overhauled folder scanning engine by decoupling synchronous thumbnail generation (thumbnails load lazily on-demand in the UI), utilizing in-memory lookup sets, pre-caching tags, and batching SQLite commits every 500 items. Scan speed exceeds **1,020 files/sec**, slashing 9,000 asset scans from ~1 hour down to under 10 seconds.
- **O(1) Selection Lookups**: Replaced $O(N)$ array lookup in the media grid with a `Set` selection matrix, eliminating UI lag when selecting items in multi-thousand asset libraries.
- **Progressive Chunk Rendering**: Implemented an `IntersectionObserver` rendering sentinel that renders an initial 150 items and streams subsequent chunks as the user scrolls, preventing DOM lockup.

---

## [1.0.3] - 2026-09-03

### Added
- **Windows Executable Version Resource**: Integrated `version_info.txt` to compile Windows File Version and Product Version metadata directly into `dist/AssetVault.exe`.
- **Authentic Branding & Favicons**: Multi-resolution canonical icons (`16x16`, `32x32`, `256x256`, `apple-touch-icon`) extracted from `assetvault.ico` and integrated across web metadata and navigation.
- **Offline Privacy Policy**: Added interactive modal dialog and documented assurance in `mds/privacy_policy.md`.
- **GitHub Community Health Suite**: Added open-source governance files (`CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`, issue/PR templates, `CITATION.cff`) achieving 100% community score.

### Fixed
- **Internal Folder Exclusion**: Fixed recursive scanner and file watcher to ignore internal system directories (`.cache/`, `db/`, `storage/`, `node_modules/`, `.git/`, `.venv/`) while scanning media at the library root.

---

## [1.0.2] - 2026-09-02

### Added
- **File Format Filter Pills**: Sub-bar filters allowing instant switching between All Files, Images, Videos, Audio, and Documents.
- **Dynamic Catalog Sizing & Select All**: Global `Ctrl + A` / `Cmd + A` shortcuts supporting instant selection across thousands of assets without hardcoded pagination barriers.
- **Common Tags Management**: Visual chip-based removal for shared tags across multi-selected assets.

### Fixed
- **Watchdog Event Suppression & WAL Concurrency**: Thread-safe event suppression preventing `StaleDataError` during batch moves, renames, and trashing operations.

---

## [1.0.1] - 2026-09-01

### Fixed
- **Strict Active Folder Inventory Scoping**: Enforced strict folder ID filtering on inventory queries.
- **Startup Orphan Cleanup**: Purged stale asset references for removed offline files during application startup.

---

## [1.0.0] - 2026-08-31

### Added
- **Standalone Windows Desktop Application**: Single portable executable (`AssetVault.exe`) powered by PyWebView + PyInstaller with zero Python or Node.js runtime prerequisites.
- **In-Place Multi-Folder Reference Engine**: Indexes and organizes media directly in original folders on local and network drives without file duplication.
- **High-Definition Video Frame Thumbnails**: Windows Shell keyframe extraction with custom play badges.
- **Hierarchical Subfolder Tree**: Collapsible nested folder tree navigation with real-time asset count badges.
- **Multi-Tag Search & Filter**: Instant search with AND-logic tag filtering matching both `#tag` chips and raw search terms.
- **Windows Explorer Integration**: Native disk operations including in-place rename, reveal in Explorer (`explorer.exe /select`), and safe Recycle Bin trashing (`send2trash`).
- **Interactive Full-Screen Media Previewer**:
  - Images: Deep zoom, pan, 90° rotate, and reset view.
  - Videos: HTML5 player with 0.5x–2x playback speed controls and scrub bar.
  - Audio: Audio player with volume slider and waveform badges.
  - PDFs: Vector-embedded document reader.
- **Real-Time File Watcher**: Background directory monitoring via Win32 `ReadDirectoryChangesW` kernel hooks with live WebSocket sync.
- **Automated Tagging**: Auto-tags on indexing including `#ext`, `#filename`, `#year`, and `#parent_folder`.
- **Process Lifecycle Hooks**: Clean shutdown on window close preventing orphaned backend processes.

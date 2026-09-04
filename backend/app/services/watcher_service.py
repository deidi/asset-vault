import os
import time
import mimetypes
import logging
import threading
from datetime import datetime
from typing import Dict, Optional, Set, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent, FileMovedEvent

from app.db.session import SessionLocal
from app.models.library_folder import LibraryFolder
from app.models.asset import Asset
from app.models.tag import Tag
from app.repositories.library_folder_repository import LibraryFolderRepository
from app.repositories.asset_repository import AssetRepository
from app.services.tag_service import TagService
from app.services.connection_manager import manager
from app.services.folder_service import SUPPORTED_EXTENSIONS, is_excluded_path

logger = logging.getLogger("assetvault.watcher")

class LibraryEventHandler(FileSystemEventHandler):
    """Handles real-time file system events for a specific watched LibraryFolder."""

    def __init__(self, folder_id: str):
        super().__init__()
        self.folder_id = folder_id
        self._debounce_lock = threading.Lock()
        self._processed_timestamps: Dict[str, float] = {}

    def _is_supported(self, file_path: str) -> bool:
        if is_excluded_path(file_path):
            return False
        _, ext = os.path.splitext(file_path)
        return ext.lower() in SUPPORTED_EXTENSIONS

    def _wait_until_stable(self, file_path: str, max_wait_sec: float = 3.0) -> bool:
        """Polls until file is accessible and stops changing size (e.g. during copy)."""
        start_time = time.time()
        last_size = -1

        while time.time() - start_time < max_wait_sec:
            if not os.path.exists(file_path):
                return False
            try:
                current_size = os.path.getsize(file_path)
                if current_size == last_size and current_size > 0:
                    return True
                last_size = current_size
                time.sleep(0.15)
            except (OSError, PermissionError):
                time.sleep(0.2)
        return os.path.exists(file_path)

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if is_excluded_path(event.src_path):
            return
        if watcher_service.is_suppressed(event.src_path):
            return
        self._handle_file_created_or_modified(event.src_path, is_new=True)

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if is_excluded_path(event.src_path):
            return
        if watcher_service.is_suppressed(event.src_path):
            return
        self._handle_file_created_or_modified(event.src_path, is_new=False)

    def on_moved(self, event: FileMovedEvent) -> None:
        if event.is_directory:
            return
        if is_excluded_path(event.src_path) and is_excluded_path(event.dest_path):
            return
        if watcher_service.is_suppressed(event.src_path) or watcher_service.is_suppressed(event.dest_path):
            return
        src_path = os.path.normpath(event.src_path)
        dest_path = os.path.normpath(event.dest_path)

        logger.info(f"File moved / renamed detected: {src_path} -> {dest_path}")

        db = SessionLocal()
        try:
            asset_repo = AssetRepository(db)
            tag_service = TagService(db)

            asset = asset_repo.find_by_storage_path(src_path)
            if not asset:
                # If old path wasn't tracked, check if dest path is a supported media file to index
                if self._is_supported(dest_path):
                    self._handle_file_created_or_modified(dest_path, is_new=True)
                return

            # If renamed to an unsupported extension, remove from index
            if not self._is_supported(dest_path):
                asset_repo.delete(asset.id)
                manager.broadcast_sync("file_deleted", {
                    "asset_id": asset.id,
                    "path": src_path,
                    "folder_id": self.folder_id
                })
                return

            new_filename = os.path.basename(dest_path)
            old_filename = asset.original_name
            old_filename_tag_name = old_filename
            new_filename_tag_name = new_filename

            asset.name = new_filename
            asset.original_name = new_filename
            asset.storage_path = dest_path
            asset.file_modified_at = datetime.utcnow()

            # Update filename tag
            updated_tags: List[Tag] = []
            for tag in asset.tags:
                if tag.name == old_filename_tag_name:
                    continue
                updated_tags.append(tag)

            new_tag = tag_service.get_or_create_tag(new_filename_tag_name)
            if new_tag not in updated_tags:
                updated_tags.append(new_tag)

            asset.tags = updated_tags
            saved = asset_repo.save(asset)

            manager.broadcast_sync("file_renamed", {
                "asset_id": saved.id,
                "name": saved.name,
                "old_path": src_path,
                "new_path": dest_path,
                "folder_id": self.folder_id,
                "tags": [{"id": t.id, "name": t.name} for t in saved.tags]
            })
            logger.info(f"Updated asset record for rename: {new_filename}")

        except Exception as e:
            logger.error(f"Error handling file rename {src_path} -> {dest_path}: {e}")
            db.rollback()
        finally:
            db.close()

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if is_excluded_path(event.src_path):
            return
        if watcher_service.is_suppressed(event.src_path):
            return
        path = os.path.normpath(event.src_path)
        logger.info(f"File deletion detected: {path}")

        db = SessionLocal()
        try:
            asset_repo = AssetRepository(db)
            asset = asset_repo.find_by_storage_path(path)
            if asset:
                asset_id = asset.id
                asset_repo.delete(asset_id)
                manager.broadcast_sync("file_deleted", {
                    "asset_id": asset_id,
                    "path": path,
                    "folder_id": self.folder_id
                })
                logger.info(f"Removed deleted asset record {asset_id} ({path})")
        except Exception as e:
            logger.error(f"Error handling file deletion {path}: {e}")
            db.rollback()
        finally:
            db.close()

    def _handle_file_created_or_modified(self, file_path: str, is_new: bool) -> None:
        norm_path = os.path.normpath(file_path)
        if not self._is_supported(norm_path):
            return

        # Debounce rapid back-to-back events on the same file
        now = time.time()
        with self._debounce_lock:
            last_time = self._processed_timestamps.get(norm_path, 0)
            if now - last_time < 0.8:
                return
            self._processed_timestamps[norm_path] = now

        if not self._wait_until_stable(norm_path):
            return

        db = SessionLocal()
        try:
            folder_repo = LibraryFolderRepository(db)
            asset_repo = AssetRepository(db)
            tag_service = TagService(db)

            folder = folder_repo.find_by_id(self.folder_id)
            if not folder or not folder.is_active:
                return

            existing = asset_repo.find_by_storage_path(norm_path)
            
            size_bytes = os.path.getsize(norm_path)
            mtime = datetime.fromtimestamp(os.path.getmtime(norm_path))
            mime_type, _ = mimetypes.guess_type(norm_path)
            filename = os.path.basename(norm_path)
            _, ext = os.path.splitext(filename)
            clean_ext = ext.lower().lstrip(".")

            if existing:
                # Update existing asset if modified
                existing.size_bytes = size_bytes
                existing.file_modified_at = mtime
                saved = asset_repo.save(existing)
                manager.broadcast_sync("file_modified", {
                    "asset_id": saved.id,
                    "name": saved.name,
                    "path": norm_path,
                    "size_bytes": saved.size_bytes,
                    "file_modified_at": saved.file_modified_at.isoformat() if saved.file_modified_at else None,
                    "folder_id": self.folder_id
                })
                return

            # Construct automatic tags (normalized without # prefix)
            tag_names: List[str] = []
            if clean_ext:
                tag_names.append(clean_ext)
            tag_names.append(filename)
            tag_names.append(str(mtime.year))

            if folder.auto_tag_folder:
                try:
                    rel_dir = os.path.relpath(os.path.dirname(norm_path), folder.path)
                    if rel_dir and rel_dir != ".":
                        for part in rel_dir.split(os.sep):
                            clean_part = part.strip()
                            if clean_part and not clean_part.startswith("."):
                                tag_names.append(clean_part)
                except Exception:
                    pass
                if folder.name:
                    tag_names.append(folder.name)

            if folder.custom_tags:
                for custom_tag in folder.custom_tags.split(","):
                    t = custom_tag.strip().lstrip("#")
                    if t:
                        tag_names.append(t)

            unique_tags = list(dict.fromkeys(tag_names))
            resolved_tags = [tag_service.get_or_create_tag(t) for t in unique_tags]

            new_asset = Asset(
                name=filename,
                original_name=filename,
                mime_type=mime_type or "application/octet-stream",
                size_bytes=size_bytes,
                storage_path=norm_path,
                folder_id=folder.id,
                file_modified_at=mtime,
                created_at=datetime.utcnow()
            )
            new_asset.tags = resolved_tags
            saved = asset_repo.save(new_asset)

            # Pre-generate thumbnail in cache
            try:
                from app.services.thumbnail_service import thumbnail_service
                thumbnail_service.get_or_generate_thumbnail(db, saved.id, 350, 350)
            except Exception as thumb_err:
                logger.debug(f"Could not pre-generate thumbnail for {saved.id}: {thumb_err}")

            manager.broadcast_sync("file_added", {
                "asset_id": saved.id,
                "name": saved.name,
                "path": norm_path,
                "mime_type": saved.mime_type,
                "size_bytes": saved.size_bytes,
                "folder_id": self.folder_id,
                "tags": [{"id": t.id, "name": t.name} for t in saved.tags]
            })
            logger.info(f"Auto-indexed newly detected file: {filename} in {folder.name}")

        except Exception as e:
            logger.error(f"Error auto-indexing file {norm_path}: {e}")
            db.rollback()
        finally:
            db.close()


class WatcherService:
    """Manages Watchdog filesystem observers for all configured library folders."""

    def __init__(self):
        self._observer: Optional[Observer] = None
        self._watches: Dict[str, Any] = {}  # folder_id -> ObservedWatch
        self._suppressed_paths: Dict[str, float] = {}  # normalized_case_path -> expire_timestamp
        self._lock = threading.Lock()

    def suppress_paths(self, paths: List[str], duration_sec: float = 5.0) -> None:
        """Temporarily suppresses watcher events for specific paths during internal operations."""
        expire_time = time.time() + duration_sec
        with self._lock:
            for p in paths:
                if p:
                    self._suppressed_paths[os.path.normcase(os.path.normpath(p))] = expire_time

    def is_suppressed(self, path: str) -> bool:
        """Checks if a path is currently suppressed from watcher event processing."""
        if not path:
            return False
        norm_case = os.path.normcase(os.path.normpath(path))
        with self._lock:
            if norm_case in self._suppressed_paths:
                if time.time() < self._suppressed_paths[norm_case]:
                    return True
                else:
                    del self._suppressed_paths[norm_case]
            return False

    def start_all(self) -> None:
        """Starts the observer engine and hooks all active library folders."""
        with self._lock:
            if self._observer and self._observer.is_alive():
                return

            self._observer = Observer()
            self._observer.daemon = True
            self._observer.start()
            logger.info("Watchdog file system observer thread started.")

            db = SessionLocal()
            try:
                folder_repo = LibraryFolderRepository(db)
                active_folders = folder_repo.find_all(active_only=True)
                for folder in active_folders:
                    self._watch_folder_internal(folder)
            except Exception as e:
                logger.error(f"Error attaching watchers on startup: {e}")
            finally:
                db.close()

    def watch_folder(self, folder: LibraryFolder) -> None:
        """Attaches a watch for a specific LibraryFolder."""
        with self._lock:
            if not self._observer or not self._observer.is_alive():
                self.start_all()
            self._watch_folder_internal(folder)

    def unwatch_folder(self, folder_id: str) -> None:
        """Stops watching a specific LibraryFolder."""
        with self._lock:
            if folder_id in self._watches and self._observer:
                watch = self._watches.pop(folder_id)
                try:
                    self._observer.unschedule(watch)
                    logger.info(f"Unscheduled watcher for folder {folder_id}")
                except Exception as e:
                    logger.warning(f"Failed to unschedule watch for {folder_id}: {e}")

    def _watch_folder_internal(self, folder: LibraryFolder) -> None:
        if not self._observer:
            return

        # Unschedule existing if any
        if folder.id in self._watches:
            try:
                self._observer.unschedule(self._watches[folder.id])
            except Exception:
                pass
            del self._watches[folder.id]

        if not os.path.exists(folder.path):
            logger.warning(f"Cannot watch non-existent folder: {folder.path}")
            return

        try:
            handler = LibraryEventHandler(folder_id=folder.id)
            watch = self._observer.schedule(
                handler,
                path=folder.path,
                recursive=folder.is_recursive
            )
            self._watches[folder.id] = watch
            logger.info(f"Watching folder '{folder.name}' at {folder.path} (recursive={folder.is_recursive})")
        except Exception as e:
            logger.error(f"Failed to schedule watch for {folder.path}: {e}")

    def stop_all(self) -> None:
        """Stops the observer thread cleanly."""
        with self._lock:
            if self._observer:
                try:
                    self._observer.stop()
                    logger.info("Watchdog observer stop signal sent.")
                except Exception as e:
                    logger.warning(f"Error stopping observer: {e}")
                finally:
                    self._observer = None
                    self._watches.clear()

# Global singleton watcher service instance
watcher_service = WatcherService()

# Ensure all observers and emitters are stopped on process exit
import atexit
atexit.register(watcher_service.stop_all)

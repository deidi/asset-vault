import os
import mimetypes
import logging
from datetime import datetime
from typing import List, Optional, Set
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.library_folder import LibraryFolder
from app.models.asset import Asset
from app.repositories.library_folder_repository import LibraryFolderRepository
from app.repositories.asset_repository import AssetRepository
from app.services.tag_service import TagService
from app.schemas.library_folder import (
    LibraryFolderCreate,
    LibraryFolderUpdate,
    LibraryFolderResponse,
    FolderScanResult,
    FolderTreeNode
)

logger = logging.getLogger("assetvault.folder_service")

# Supported media extensions bundle
IMAGE_EXTENSIONS: Set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".tiff", ".ico", ".jfif"
}
VIDEO_EXTENSIONS: Set[str] = {
    ".mp4", ".webm", ".mov", ".mkv", ".avi", ".wmv", ".flv", ".m4v"
}
AUDIO_EXTENSIONS: Set[str] = {
    ".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma"
}
DOCUMENT_EXTENSIONS: Set[str] = {
    ".pdf"
}
SUPPORTED_EXTENSIONS: Set[str] = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS | DOCUMENT_EXTENSIONS

# Directories and paths that must never be scanned, indexed, or watched
EXCLUDED_DIR_NAMES: Set[str] = {
    ".cache", "cache",
    ".git", ".github", ".vscode", ".agents", ".idea",
    ".venv", "venv", "env", ".env", "__pycache__",
    "node_modules",
    "backend",
    "frontend",
    "public",
    "storage",
    "dist",
    "build",
    "tests",
    "tasks",
    "docs",
    "system volume information",
    "$recycle.bin",
    "$recbin",
}

def is_excluded_dir_name(dir_name: str) -> bool:
    """Returns True if the directory name matches system or internal application folders."""
    if not dir_name:
        return True
    d = dir_name.strip().lower()
    if d.startswith((".", "$")):
        return True
    return d in EXCLUDED_DIR_NAMES

def is_excluded_path(path: str) -> bool:
    """Returns True if any component of the file path is an excluded/internal directory or file."""
    if not path:
        return True
    norm = os.path.normpath(path)
    parts = norm.split(os.sep)

    # Check each parent directory component
    for part in parts[:-1]:
        p = part.strip().lower()
        if p.endswith(":"):  # Drive letter e.g. "C:"
            continue
        if p.startswith((".", "$")) or p in EXCLUDED_DIR_NAMES:
            return True

    # Check the final file or directory name
    final_name = parts[-1].strip().lower()
    if final_name.startswith((".", "~$")) or final_name.endswith((".tmp", ".crdownload", ".part", ".lock")):
        return True
    if os.path.isdir(norm) and (final_name.startswith((".", "$")) or final_name in EXCLUDED_DIR_NAMES):
        return True

    return False



class FolderService:
    def __init__(self, db: Session):
        self.db = db
        self.folder_repo = LibraryFolderRepository(db)
        self.asset_repo = AssetRepository(db)
        self.tag_service = TagService(db)

    def add_folder(self, payload: LibraryFolderCreate) -> LibraryFolderResponse:
        norm_path = os.path.normpath(payload.path.strip())
        if not os.path.isdir(norm_path):
            raise ValueError(f"Directory path does not exist on disk: '{norm_path}'")

        existing = self.folder_repo.find_by_path(norm_path)
        if existing:
            raise ValueError(f"Folder is already registered in library: '{norm_path}'")

        folder_name = payload.name.strip() if payload.name and payload.name.strip() else os.path.basename(norm_path) or norm_path

        custom_tags_str = None
        if payload.custom_tags:
            custom_tags_str = ",".join([t.strip().lstrip("#") for t in payload.custom_tags if t.strip()])

        folder = LibraryFolder(
            path=norm_path,
            name=folder_name,
            is_recursive=payload.is_recursive,
            auto_tag_folder=payload.auto_tag_folder,
            custom_tags=custom_tags_str,
            is_active=True
        )
        saved = self.folder_repo.create(folder)
        
        # Dynamically attach file system watcher if watcher service is active
        try:
            from app.services.watcher_service import watcher_service
            if watcher_service._observer and watcher_service._observer.is_alive():
                watcher_service.watch_folder(saved)
        except Exception as e:
            logger.warning(f"Could not attach watcher for new folder: {e}")

        return self._to_response(saved)

    def list_folders(self, active_only: bool = False) -> List[LibraryFolderResponse]:
        folders = self.folder_repo.find_all(active_only=active_only)
        return [self._to_response(f) for f in folders]

    def get_folder(self, folder_id: str) -> Optional[LibraryFolderResponse]:
        folder = self.folder_repo.find_by_id(folder_id)
        return self._to_response(folder) if folder else None

    def update_folder(self, folder_id: str, payload: LibraryFolderUpdate) -> LibraryFolderResponse:
        folder = self.folder_repo.find_by_id(folder_id)
        if not folder:
            raise ValueError(f"Library folder with ID '{folder_id}' not found.")

        if payload.name is not None:
            folder.name = payload.name.strip()
        if payload.is_recursive is not None:
            folder.is_recursive = payload.is_recursive
        if payload.auto_tag_folder is not None:
            folder.auto_tag_folder = payload.auto_tag_folder
        if payload.is_active is not None:
            folder.is_active = payload.is_active
        if payload.custom_tags is not None:
            folder.custom_tags = ",".join([t.strip().lstrip("#") for t in payload.custom_tags if t.strip()])

        saved = self.folder_repo.save(folder)
        
        # Update watcher state if watcher service is active
        try:
            from app.services.watcher_service import watcher_service
            if watcher_service._observer and watcher_service._observer.is_alive():
                if saved.is_active:
                    watcher_service.watch_folder(saved)
                else:
                    watcher_service.unwatch_folder(saved.id)
        except Exception as e:
            logger.warning(f"Could not update watcher state for folder: {e}")

        return self._to_response(saved)

    def delete_folder(self, folder_id: str) -> bool:
        folder = self.folder_repo.find_by_id(folder_id)
        if not folder:
            return False

        try:
            from app.services.watcher_service import watcher_service
            if watcher_service._observer and watcher_service._observer.is_alive():
                watcher_service.unwatch_folder(folder_id)
        except Exception as e:
            logger.warning(f"Could not unwatch deleted folder: {e}")

        # De-index all assets associated with this folder (files on disk are NOT deleted)
        try:
            norm_path = os.path.normpath(folder.path)
            assets_to_delete = self.db.query(Asset).filter(
                or_(
                    Asset.folder_id == folder_id,
                    Asset.storage_path == norm_path,
                    Asset.storage_path.startswith(norm_path + os.sep),
                    Asset.storage_path.startswith(norm_path + "/")
                )
            ).all()
            for asset in assets_to_delete:
                self.db.delete(asset)
            self.db.commit()
        except Exception as e:
            logger.warning(f"Could not de-index assets for folder {folder_id}: {e}")

        # Delete folder record
        res = self.folder_repo.delete(folder_id)

        # Clean up any orphaned tags that no longer have associated assets
        try:
            from app.services.tag_service import TagService
            TagService(self.db).delete_unused_tags()
        except Exception as e:
            logger.warning(f"Could not clean unused tags: {e}")

        return res

    def scan_folder(self, folder_id: str) -> FolderScanResult:
        folder = self.folder_repo.find_by_id(folder_id)
        if not folder:
            raise ValueError(f"Library folder with ID '{folder_id}' not found.")

        if not os.path.exists(folder.path):
            raise FileNotFoundError(f"Folder directory does not exist on disk: {folder.path}")

        total_scanned = 0
        newly_indexed = 0
        already_indexed = 0
        errors: List[str] = []

        # Clean up any previously indexed assets in this folder that match excluded paths
        try:
            existing_folder_assets = self.db.query(Asset).filter(Asset.folder_id == folder.id).all()
            for a in existing_folder_assets:
                if a.storage_path and is_excluded_path(a.storage_path):
                    self.db.delete(a)
            self.db.commit()
        except Exception as e:
            logger.warning(f"Error purging excluded assets for folder {folder.id}: {e}")

        # Find all media files
        file_paths: List[str] = []
        if folder.is_recursive:
            for root, dirs, filenames in os.walk(folder.path, followlinks=True):
                # Exclude hidden, system, and unwanted directories from traversal
                dirs[:] = [d for d in dirs if not is_excluded_dir_name(d)]
                for filename in filenames:
                    file_abs = os.path.normpath(os.path.join(root, filename))
                    if is_excluded_path(file_abs):
                        continue
                    _, ext = os.path.splitext(filename)
                    if ext.lower() in SUPPORTED_EXTENSIONS:
                        file_paths.append(file_abs)
        else:
            try:
                for entry in os.scandir(folder.path):
                    if entry.is_file():
                        entry_abs = os.path.normpath(entry.path)
                        if is_excluded_path(entry_abs):
                            continue
                        _, ext = os.path.splitext(entry.name)
                        if ext.lower() in SUPPORTED_EXTENSIONS:
                            file_paths.append(entry_abs)
            except Exception as e:
                errors.append(f"Error scanning folder root: {str(e)}")

        total_scanned = len(file_paths)

        # Parse custom tags list from folder settings
        configured_custom_tags: List[str] = []
        if folder.custom_tags:
            configured_custom_tags = [t.strip() for t in folder.custom_tags.split(",") if t.strip()]

        for file_path in file_paths:
            try:
                # Check if file already indexed
                existing_asset = self.asset_repo.find_by_storage_path(file_path)
                if existing_asset:
                    already_indexed += 1
                    continue

                filename = os.path.basename(file_path)
                _, ext = os.path.splitext(filename)
                clean_ext = ext.lower().lstrip(".")

                size_bytes = os.path.getsize(file_path)
                mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                mime_type, _ = mimetypes.guess_type(file_path)

                # Determine tag set
                tag_names_to_add: List[str] = []
                
                # 1. System extension tag
                if clean_ext:
                    tag_names_to_add.append(f"#{clean_ext}")

                # 2. System filename tag
                tag_names_to_add.append(f"#{filename}")

                # 3. Year tag
                year_tag = f"#{mtime.year}"
                tag_names_to_add.append(year_tag)

                # 4. Folder name tags (all directory levels down to file)
                if folder.auto_tag_folder:
                    try:
                        rel_dir = os.path.relpath(os.path.dirname(file_path), folder.path)
                        if rel_dir and rel_dir != ".":
                            for part in rel_dir.split(os.sep):
                                clean_part = part.strip()
                                if clean_part and not clean_part.startswith("."):
                                    tag_names_to_add.append(f"#{clean_part}")
                    except Exception:
                        pass
                    if folder.name:
                        tag_names_to_add.append(f"#{folder.name}")

                # 5. Custom configured folder tags
                for custom_tag in configured_custom_tags:
                    tag_names_to_add.append(f"#{custom_tag}" if not custom_tag.startswith("#") else custom_tag)

                # Deduplicate tags
                unique_tags = list(dict.fromkeys(tag_names_to_add))
                resolved_tags = [self.tag_service.get_or_create_tag(t) for t in unique_tags]

                # Create Asset record
                asset = Asset(
                    name=filename,
                    original_name=filename,
                    mime_type=mime_type or "application/octet-stream",
                    size_bytes=size_bytes,
                    storage_path=file_path,
                    folder_id=folder.id,
                    file_modified_at=mtime,
                    created_at=datetime.utcnow()
                )
                asset.tags = resolved_tags
                saved_asset = self.asset_repo.save(asset)
                newly_indexed += 1

                # Pre-generate thumbnail in cache
                try:
                    from app.services.thumbnail_service import thumbnail_service
                    thumbnail_service.get_or_generate_thumbnail(self.db, saved_asset.id, 350, 350)
                except Exception as thumb_err:
                    logger.debug(f"Could not pre-generate thumbnail for {saved_asset.id}: {thumb_err}")

            except Exception as e:
                logger.error(f"Error indexing file {file_path}: {e}")
                errors.append(f"{file_path}: {str(e)}")

        return FolderScanResult(
            folder_id=folder.id,
            folder_path=folder.path,
            total_scanned=total_scanned,
            newly_indexed=newly_indexed,
            already_indexed=already_indexed,
            errors=errors
        )

    def scan_all_active_folders(self) -> List[FolderScanResult]:
        active_folders = self.folder_repo.find_all(active_only=True)
        results = []
        for folder in active_folders:
            try:
                results.append(self.scan_folder(folder.id))
            except Exception as e:
                logger.error(f"Failed scanning folder {folder.path}: {e}")
                results.append(FolderScanResult(
                    folder_id=folder.id,
                    folder_path=folder.path,
                    total_scanned=0,
                    newly_indexed=0,
                    already_indexed=0,
                    errors=[str(e)]
                ))
        return results

    def get_folder_tree(self, folder_id: str, max_depth: int = 4) -> FolderTreeNode:
        """Constructs a nested subfolder tree hierarchy with asset counts for a library folder."""
        folder = self.folder_repo.find_by_id(folder_id)
        if not folder:
            raise ValueError(f"Library folder with ID '{folder_id}' not found.")
        if not os.path.exists(folder.path):
            raise FileNotFoundError(f"Folder directory does not exist on disk: {folder.path}")

        # Fetch all asset storage paths for this folder to compute asset counts per directory
        assets = self.db.query(Asset.storage_path).filter(Asset.folder_id == folder.id).all()
        
        # Build fast O(1) directory count dictionary
        from collections import defaultdict
        dir_counts: Dict[str, int] = defaultdict(int)
        norm_root = os.path.normpath(folder.path).lower()

        for a in assets:
            if not a[0]:
                continue
            cur = os.path.normpath(os.path.dirname(a[0]))
            while cur:
                dir_counts[cur.lower()] += 1
                parent = os.path.dirname(cur)
                if not parent or parent == cur or cur.lower() == norm_root:
                    break
                cur = parent

        def build_tree_node(dir_path: str, rel_path: str = "", current_depth: int = 0) -> FolderTreeNode:
            norm_dir = os.path.normpath(dir_path)
            name = folder.name if not rel_path else (os.path.basename(norm_dir) or folder.name)
            dir_asset_count = dir_counts.get(norm_dir.lower(), 0)

            children: List[FolderTreeNode] = []
            if current_depth < max_depth:
                try:
                    subdirs = []
                    with os.scandir(norm_dir) as entries:
                        for entry in entries:
                            if entry.is_dir() and not is_excluded_dir_name(entry.name):
                                subdirs.append(entry.name)
                    subdirs.sort(key=lambda s: s.lower())
                    for sub in subdirs:
                        sub_abs = os.path.join(norm_dir, sub)
                        sub_rel = os.path.join(rel_path, sub) if rel_path else sub
                        children.append(build_tree_node(sub_abs, sub_rel, current_depth + 1))
                except Exception as e:
                    logger.warning(f"Failed scanning subdirectories for {norm_dir}: {e}")

            return FolderTreeNode(
                name=name,
                path=norm_dir,
                relative_path=rel_path,
                asset_count=dir_asset_count,
                children=children
            )

        return build_tree_node(folder.path, "", 0)

    def open_folder_picker_dialog(self) -> Optional[str]:
        """Opens a native OS folder selection dialog."""
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            selected_dir = filedialog.askdirectory(title="Select Media Folder for AssetVault")
            root.destroy()
            return os.path.normpath(selected_dir) if selected_dir else None
        except Exception as e:
            logger.warning(f"Native folder picker fallback failed: {e}")
            return None

    def _to_response(self, folder: LibraryFolder) -> LibraryFolderResponse:
        asset_count = self.asset_repo.count_by_folder_id(folder.id)
        return LibraryFolderResponse(
            id=folder.id,
            path=folder.path,
            name=folder.name,
            is_recursive=folder.is_recursive,
            auto_tag_folder=folder.auto_tag_folder,
            custom_tags=folder.custom_tags,
            is_active=folder.is_active,
            asset_count=asset_count,
            created_at=folder.created_at
        )

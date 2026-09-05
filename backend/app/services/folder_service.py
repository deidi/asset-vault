import os
import mimetypes
import logging
from datetime import datetime
from typing import List, Optional, Set, Dict
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.library_folder import LibraryFolder
from app.models.asset import Asset
from app.models.tag import Tag
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

from app.services.category_service import CategoryService, DEFAULT_CATEGORY_EXTENSIONS

# Supported media extensions bundle (defaults, kept updated by CategoryService)
IMAGE_EXTENSIONS: Set[str] = set(DEFAULT_CATEGORY_EXTENSIONS["image"])
VIDEO_EXTENSIONS: Set[str] = set(DEFAULT_CATEGORY_EXTENSIONS["video"])
AUDIO_EXTENSIONS: Set[str] = set(DEFAULT_CATEGORY_EXTENSIONS["audio"])
DOCUMENT_EXTENSIONS: Set[str] = set(DEFAULT_CATEGORY_EXTENSIONS["document"])
MEDIA_EXTENSIONS: Set[str] = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS | DOCUMENT_EXTENSIONS
SUPPORTED_EXTENSIONS: Set[str] = MEDIA_EXTENSIONS

def categorize_file(path_or_name: str, mime_type: Optional[str] = None) -> str:
    """Classifies a file into: 'image', 'video', 'audio', 'document', or 'other'."""
    _, ext = os.path.splitext(path_or_name)
    clean_ext = ext.lower()
    clean_mime = (mime_type or "").lower()

    active = CategoryService.get_active_extensions()
    img_exts = active.get("image", IMAGE_EXTENSIONS)
    vid_exts = active.get("video", VIDEO_EXTENSIONS)
    aud_exts = active.get("audio", AUDIO_EXTENSIONS)
    doc_exts = active.get("document", DOCUMENT_EXTENSIONS)

    # When an extension is present, classification is STRICTLY governed by registered extensions
    if clean_ext:
        if clean_ext in img_exts:
            return "image"
        if clean_ext in vid_exts:
            return "video"
        if clean_ext in aud_exts:
            return "audio"
        if clean_ext in doc_exts:
            return "document"
        return "other"

    # Only fall back to MIME type if the file has no extension at all
    if clean_mime:
        if clean_mime.startswith("image/"):
            return "image"
        if clean_mime.startswith("video/"):
            return "video"
        if clean_mime.startswith("audio/"):
            return "audio"
        if (
            "pdf" in clean_mime
            or "document" in clean_mime
            or clean_mime.startswith("text/")
        ):
            return "document"

    return "other"

# Directories and files that must be ignored to prevent feedback loops and indexing internal app state
EXCLUDED_DIR_NAMES: Set[str] = {
    ".cache", "cache",
    "db",
    "storage",
    ".git", ".github", ".vscode", ".agents", ".idea",
    ".venv", "venv", "env", "__pycache__",
    "node_modules",
    "system volume information",
    "$recycle.bin",
    "$recbin",
}

EXCLUDED_FILENAMES: Set[str] = {
    "assetvault.sqlite",
    "assetvault.sqlite-wal",
    "assetvault.sqlite-shm",
    "settings.json",
    "thumbs.db",
    ".ds_store",
}

def is_excluded_dir_name(dir_name: str) -> bool:
    """Returns True if the directory name matches internal app cache, db, storage or system folders."""
    if not dir_name:
        return True
    d = dir_name.strip().lower()
    if d.startswith((".", "$")):
        return True
    return d in EXCLUDED_DIR_NAMES

def is_excluded_path(path: str) -> bool:
    """Returns True if the path is inside cache, db, storage, or internal/system files."""
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
    if final_name in EXCLUDED_FILENAMES:
        return True
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
        orphans_purged = 0
        moved_reconciled = 0
        errors: List[str] = []

        # 1. Clean up any previously indexed assets in this folder that match excluded paths
        try:
            excluded_assets = self.db.query(Asset).filter(Asset.folder_id == folder.id).all()
            for a in excluded_assets:
                if a.storage_path and is_excluded_path(a.storage_path):
                    self.db.delete(a)
            self.db.commit()
        except Exception as e:
            logger.warning(f"Error purging excluded assets for folder {folder.id}: {e}")

        # 2. Map existing assets for this folder into existing (valid on disk) vs missing
        existing_assets = self.db.query(Asset).filter(Asset.folder_id == folder.id).all()
        existing_paths: Dict[str, Asset] = {}
        missing_by_name: Dict[str, List[Asset]] = {}

        for a in existing_assets:
            if a.storage_path:
                norm_p = os.path.normpath(a.storage_path)
                if os.path.exists(norm_p):
                    existing_paths[norm_p] = a
                else:
                    filename = a.name or os.path.basename(norm_p)
                    missing_by_name.setdefault(filename, []).append(a)

        # 3. Discover all valid files currently present on disk (including non-media files)
        file_paths: List[str] = []
        if folder.is_recursive:
            for root, dirs, filenames in os.walk(folder.path, followlinks=True):
                # Exclude hidden, system, and unwanted directories from traversal immediately
                dirs[:] = [d for d in dirs if not is_excluded_dir_name(d)]
                for filename in filenames:
                    file_abs = os.path.normpath(os.path.join(root, filename))
                    if not is_excluded_path(file_abs):
                        file_paths.append(file_abs)
        else:
            try:
                for entry in os.scandir(folder.path):
                    if entry.is_file():
                        entry_abs = os.path.normpath(entry.path)
                        if not is_excluded_path(entry_abs):
                            file_paths.append(entry_abs)
            except Exception as e:
                errors.append(f"Error scanning folder root: {str(e)}")

        total_scanned = len(file_paths)

        # Parse custom tags list from folder settings
        configured_custom_tags: List[str] = []
        if folder.custom_tags:
            configured_custom_tags = [t.strip() for t in folder.custom_tags.split(",") if t.strip()]

        # 4. Pre-cache all tags in memory for fast lookup/creation
        tags_cache: Dict[str, Tag] = {t.name.lower(): t for t in self.db.query(Tag).all()}

        # 5. Process files on disk with batched commits and smart move reconciliation
        batch_counter = 0
        for file_path in file_paths:
            try:
                # If already indexed at this exact path, count and continue
                if file_path in existing_paths:
                    already_indexed += 1
                    continue

                filename = os.path.basename(file_path)
                _, ext = os.path.splitext(filename)
                clean_ext = ext.lower().lstrip(".")

                size_bytes = os.path.getsize(file_path)
                mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                mime_type, _ = mimetypes.guess_type(file_path)
                category = categorize_file(file_path, mime_type)

                # Check if this is a moved file previously at another path in this folder
                candidate_list = missing_by_name.get(filename)
                if candidate_list:
                    matched_idx = 0
                    for idx, candidate in enumerate(candidate_list):
                        if candidate.size_bytes == size_bytes:
                            matched_idx = idx
                            break
                    matched_asset = candidate_list.pop(matched_idx)
                    if not candidate_list:
                        del missing_by_name[filename]

                    # Reconcile moved asset in-place, preserving UUID, custom tags, and history
                    matched_asset.storage_path = file_path
                    matched_asset.size_bytes = size_bytes
                    matched_asset.file_modified_at = mtime
                    matched_asset.category = category
                    if mime_type:
                        matched_asset.mime_type = mime_type
                    existing_paths[file_path] = matched_asset
                    moved_reconciled += 1
                    already_indexed += 1
                    batch_counter += 1
                    if batch_counter % 500 == 0:
                        self.db.commit()
                    continue

                # Brand new asset to index
                tag_names_to_add: List[str] = []
                if clean_ext:
                    tag_names_to_add.append(f"#{clean_ext}")
                tag_names_to_add.append(f"#{filename}")
                tag_names_to_add.append(f"#{mtime.year}")

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

                for custom_tag in configured_custom_tags:
                    tag_names_to_add.append(f"#{custom_tag}" if not custom_tag.startswith("#") else custom_tag)

                unique_tags = list(dict.fromkeys(tag_names_to_add))
                resolved_tags: List[Tag] = []
                for t_name in unique_tags:
                    t_lower = t_name.lower()
                    if t_lower in tags_cache:
                        resolved_tags.append(tags_cache[t_lower])
                    else:
                        new_tag = Tag(name=t_name)
                        self.db.add(new_tag)
                        tags_cache[t_lower] = new_tag
                        resolved_tags.append(new_tag)

                asset = Asset(
                    name=filename,
                    original_name=filename,
                    mime_type=mime_type or "application/octet-stream",
                    size_bytes=size_bytes,
                    storage_path=file_path,
                    folder_id=folder.id,
                    category=category,
                    file_modified_at=mtime,
                    created_at=datetime.utcnow()
                )
                asset.tags = resolved_tags
                self.db.add(asset)
                existing_paths[file_path] = asset
                newly_indexed += 1
                batch_counter += 1

                if batch_counter % 500 == 0:
                    self.db.commit()

            except Exception as e:
                logger.error(f"Error indexing file {file_path}: {e}")
                errors.append(f"{file_path}: {str(e)}")

        # 6. Purge orphaned records for assets no longer on disk
        for remaining_missing_list in missing_by_name.values():
            for orphan in remaining_missing_list:
                try:
                    self.db.delete(orphan)
                    orphans_purged += 1
                except Exception as del_err:
                    logger.debug(f"Failed deleting orphaned asset {orphan.id}: {del_err}")

        # Final commit of any remaining staged additions, updates, or deletions
        try:
            self.db.commit()
        except Exception as commit_err:
            logger.error(f"Commit error during folder scan: {commit_err}")
            self.db.rollback()

        # Clean up any unused tags
        try:
            self.tag_service.delete_unused_tags()
        except Exception:
            pass

        return FolderScanResult(
            folder_id=folder.id,
            folder_path=folder.path,
            total_scanned=total_scanned,
            newly_indexed=newly_indexed,
            already_indexed=already_indexed,
            orphans_purged=orphans_purged,
            moved_reconciled=moved_reconciled,
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

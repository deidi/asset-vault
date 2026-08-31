import os
import sys
import shutil
import logging
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import send2trash

from app.models.asset import Asset
from app.models.tag import Tag
from app.repositories.asset_repository import AssetRepository
from app.services.tag_service import TagService

logger = logging.getLogger("assetvault.explorer")

class ExplorerService:
    def __init__(self, db: Session):
        self.db = db
        self.asset_repo = AssetRepository(db)
        self.tag_service = TagService(db)

    def reveal_in_explorer(
        self,
        target_path: Optional[str] = None,
        asset_id: Optional[str] = None,
        folder_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Opens Windows File Explorer with the specified file selected, or opens a folder."""
        resolved_path = None
        if asset_id:
            asset = self.asset_repo.find_by_id(asset_id)
            if not asset:
                return {"status": "error", "message": f"Asset {asset_id} not found."}
            if asset.storage_path and os.path.exists(asset.storage_path):
                resolved_path = asset.storage_path
            else:
                from app.services.asset_service import AssetService
                asset_service = AssetService(self.db)
                resolved_path = asset_service.get_asset_file_path(asset.id)
        elif folder_id:
            from app.repositories.library_folder_repository import LibraryFolderRepository
            folder_repo = LibraryFolderRepository(self.db)
            folder = folder_repo.find_by_id(folder_id)
            if not folder:
                return {"status": "error", "message": f"Folder {folder_id} not found."}
            resolved_path = folder.path
        elif target_path:
            resolved_path = target_path

        if not resolved_path:
            return {"status": "error", "message": "No valid path or asset_id provided."}

        norm_path = os.path.normpath(resolved_path)
        if not os.path.exists(norm_path):
            return {"status": "error", "message": f"File does not exist at path: {norm_path}"}

        try:
            if sys.platform == "win32":
                if os.path.isdir(norm_path):
                    os.startfile(norm_path)
                else:
                    # Windows explorer requires: explorer.exe /select,"C:\path\to\file"
                    # Passing a single string to Popen ensures /select, is not quoted by subprocess
                    subprocess.Popen(f'explorer.exe /select,"{norm_path}"')
            else:
                parent_dir = norm_path if os.path.isdir(norm_path) else os.path.dirname(norm_path)
                if sys.platform == "darwin":
                    subprocess.Popen(["open", parent_dir])
                else:
                    subprocess.Popen(["xdg-open", parent_dir])
            return {"status": "success", "revealed_path": norm_path}
        except Exception as e:
            logger.error(f"Failed to open explorer for {norm_path}: {e}")
            return {"status": "error", "message": str(e)}

    def rename_on_disk(self, asset_id: str, new_name: str) -> Asset:
        """Renames the asset file on disk and updates its DB record and filename tag."""
        asset = self.asset_repo.find_by_id(asset_id)
        if not asset:
            raise ValueError(f"Asset with ID '{asset_id}' not found.")

        current_path = os.path.normpath(asset.storage_path) if asset.storage_path else None
        if not current_path or not os.path.exists(current_path):
            raise FileNotFoundError(f"Underlying file not found on disk at: {current_path}")

        parent_dir = os.path.dirname(current_path)
        _, old_ext = os.path.splitext(current_path)
        
        cleaned_new_name = new_name.strip()
        new_base, new_ext = os.path.splitext(cleaned_new_name)
        if not new_ext:
            # Retain original extension if user didn't specify one
            final_filename = f"{new_base}{old_ext}"
        else:
            final_filename = cleaned_new_name

        target_path = os.path.normpath(os.path.join(parent_dir, final_filename))

        if target_path == current_path:
            return asset

        if os.path.exists(target_path):
            raise FileExistsError(f"A file named '{final_filename}' already exists in the same folder.")

        # Rename file on disk
        os.replace(current_path, target_path)

        # Update Asset in DB
        old_filename_tag_name = f"#{asset.original_name}"
        new_filename_tag_name = f"#{final_filename}"
        
        asset.name = final_filename
        asset.original_name = final_filename
        asset.storage_path = target_path
        asset.file_modified_at = datetime.utcnow()

        # Update tags: replace old filename tag with new filename tag
        updated_tags: List[Tag] = []
        for tag in asset.tags:
            if tag.name == old_filename_tag_name:
                continue
            updated_tags.append(tag)
        
        new_filename_tag = self.tag_service.get_or_create_tag(new_filename_tag_name)
        if new_filename_tag not in updated_tags:
            updated_tags.append(new_filename_tag)
        
        asset.tags = updated_tags
        self.asset_repo.save(asset)
        return asset

    def trash_to_recycle_bin(self, asset_id: str) -> Dict[str, Any]:
        """Safely moves the asset file to the Windows Recycle Bin and removes DB record."""
        asset = self.asset_repo.find_by_id(asset_id)
        if not asset:
            raise ValueError(f"Asset with ID '{asset_id}' not found.")

        from app.services.asset_service import AssetService
        asset_service = AssetService(self.db)
        abs_target_path = asset_service.get_asset_file_path(asset.id)

        if abs_target_path and os.path.exists(abs_target_path):
            try:
                send2trash.send2trash(abs_target_path)
            except Exception as e:
                logger.warning(f"send2trash failed for {abs_target_path}, attempting os.remove: {e}")
                try:
                    os.remove(abs_target_path)
                except Exception as ex:
                    logger.error(f"Failed to remove file {abs_target_path}: {ex}")

        self.asset_repo.delete(asset_id)
        return {"status": "success", "deleted_asset_id": asset_id, "trashed_path": abs_target_path}

    def batch_trash(self, asset_ids: List[str]) -> Dict[str, Any]:
        """Trashes multiple assets to Windows Recycle Bin."""
        trashed_count = 0
        errors: List[str] = []
        
        for asset_id in asset_ids:
            try:
                self.trash_to_recycle_bin(asset_id)
                trashed_count += 1
            except Exception as e:
                errors.append(f"Asset {asset_id}: {str(e)}")

        return {
            "status": "success" if not errors else "partial",
            "total_requested": len(asset_ids),
            "trashed_count": trashed_count,
            "errors": errors
        }

    def batch_move(self, asset_ids: List[str], destination_folder: str) -> Dict[str, Any]:
        """Moves assets on disk to a destination directory and updates their paths in DB."""
        dest_dir = os.path.normpath(destination_folder)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)

        moved_count = 0
        errors: List[str] = []

        for asset_id in asset_ids:
            asset = self.asset_repo.find_by_id(asset_id)
            if not asset or not asset.storage_path:
                errors.append(f"Asset {asset_id} not found or missing path.")
                continue

            current_path = os.path.normpath(asset.storage_path)
            if not os.path.exists(current_path):
                errors.append(f"File not found on disk: {current_path}")
                continue

            filename = os.path.basename(current_path)
            target_path = os.path.normpath(os.path.join(dest_dir, filename))

            try:
                shutil.move(current_path, target_path)
                asset.storage_path = target_path
                asset.file_modified_at = datetime.utcnow()
                self.asset_repo.save(asset)
                moved_count += 1
            except Exception as e:
                errors.append(f"Failed moving {filename}: {str(e)}")

        return {
            "status": "success" if not errors else "partial",
            "total_requested": len(asset_ids),
            "moved_count": moved_count,
            "destination": dest_dir,
            "errors": errors
        }

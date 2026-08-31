from sqlalchemy import or_, desc, asc
from sqlalchemy.orm import Session
from app.models.asset import Asset
from app.models.tag import Tag
from app.models.library_folder import LibraryFolder
from app.repositories.asset_repository import AssetRepository
from app.services.tag_service import TagService
from app.schemas.asset import AssetCreate, AssetUpdate
from typing import List, Optional, Union
from datetime import datetime
from fastapi import UploadFile
from PIL import Image
import io
import csv
import hashlib
import logging
import uuid
import os
import sys
import math
import zipfile
import re

class AssetService:
    def __init__(self, db: Session):
        self.db = db
        self.asset_repo = AssetRepository(db)
        self.tag_service = TagService(db)

    def _get_settings_path(self) -> str:
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            return os.path.abspath(os.path.join(exe_dir, "db", "settings.json"))
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            return os.path.abspath(os.path.join(current_dir, "..", "..", "..", "backend", "db", "settings.json"))

    def _get_storage_dir(self) -> str:
        settings_path = self._get_settings_path()
        if os.path.exists(settings_path):
            try:
                import json
                with open(settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    custom_dir = data.get("storage_dir")
                    if custom_dir:
                        return os.path.abspath(custom_dir)
            except Exception:
                pass

        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            storage_dir = os.path.abspath(os.path.join(exe_dir, "storage"))
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            storage_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "..", "storage"))
        return storage_dir

    def update_storage_dir(self, new_dir: str) -> dict:
        import shutil
        new_dir = os.path.abspath(new_dir.strip())
        old_dir = self._get_storage_dir()
        
        # If the directory is exactly the same, do nothing
        if new_dir == old_dir:
            return {"status": "success", "storage_dir": new_dir, "moved_files": 0}
            
        # Ensure new directory exists
        try:
            os.makedirs(new_dir, exist_ok=True)
        except Exception as e:
            return {"status": "error", "message": f"Could not create new directory: {str(e)}"}
            
        # Verify writing to the new directory works
        test_file = os.path.join(new_dir, f".write_test_{uuid.uuid4().hex}")
        try:
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
        except Exception as e:
            return {"status": "error", "message": f"New directory is not writable: {str(e)}"}
            
        # Move all existing files from old_dir to new_dir
        moved_count = 0
        errors = []
        if os.path.exists(old_dir):
            for filename in os.listdir(old_dir):
                old_file_path = os.path.join(old_dir, filename)
                if os.path.isfile(old_file_path):
                    new_file_path = os.path.join(new_dir, filename)
                    try:
                        shutil.move(old_file_path, new_file_path)
                        moved_count += 1
                    except Exception as e:
                        errors.append(f"Failed to move {filename}: {str(e)}")
                        
        if errors:
            return {"status": "error", "message": f"Failed to move some files: {', '.join(errors)}"}
            
        # Save new path to settings.json
        settings_path = self._get_settings_path()
        try:
            import json
            settings_dir = os.path.dirname(settings_path)
            if settings_dir:
                os.makedirs(settings_dir, exist_ok=True)
                
            data = {}
            if os.path.exists(settings_path):
                with open(settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data["storage_dir"] = new_dir
            
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            return {"status": "error", "message": f"Failed to save settings file: {str(e)}"}
            
        return {"status": "success", "storage_dir": new_dir, "moved_files": moved_count}

    def get_all_assets(self) -> List[Asset]:
        return self.asset_repo.find_all()

    def get_asset_by_id(self, id: str) -> Optional[Asset]:
        return self.asset_repo.find_by_id(id)

    def get_asset_file_path(self, id: str) -> Optional[str]:
        asset = self.asset_repo.find_by_id(id)
        if not asset or not asset.storage_path:
            return None
        # 1. Check if storage_path points directly to an existing in-place file
        if os.path.exists(asset.storage_path):
            return os.path.abspath(asset.storage_path)
        # 2. Check internal storage fallback
        storage_file = os.path.abspath(os.path.join(self._get_storage_dir(), os.path.basename(asset.storage_path)))
        if os.path.exists(storage_file):
            return storage_file
        return os.path.abspath(asset.storage_path)

    def _generate_unique_name(self, base_name: str) -> str:
        name_without_ext, ext = os.path.splitext(base_name)
        existing_assets = self.db.query(Asset).filter(Asset.name.ilike(base_name)).all()
        if not existing_assets:
            return base_name
            
        counter = 1
        new_name = f"{name_without_ext} ({counter}){ext}"
        while self.db.query(Asset).filter(Asset.name.ilike(new_name)).first():
            counter += 1
            new_name = f"{name_without_ext} ({counter}){ext}"
            
        return new_name

    def delete_asset(self, id: str) -> bool:
        asset = self.asset_repo.find_by_id(id)
        if not asset:
            return False

        # Resolve the absolute path to the stored file before removing the DB record.
        # storage_path is relative to the project root, e.g. "storage/<uuid>.ext".
        abs_file_path = os.path.abspath(os.path.join(self._get_storage_dir(), os.path.basename(asset.storage_path)))

        deleted = self.asset_repo.delete(id)

        if deleted and asset.storage_path:
            if os.path.exists(abs_file_path):
                try:
                    os.remove(abs_file_path)
                except OSError as exc:
                    # Log but do not fail — the DB record is already gone.
                    logging.getLogger("assetvault").warning(
                        "Could not remove file %s: %s", abs_file_path, exc
                    )

        return deleted



    def upload_asset(self, asset_data: AssetCreate) -> Asset:
        tag_objects = []
        all_tags = list(asset_data.tags) if asset_data.tags else []
        filename = asset_data.originalName.strip() if asset_data.originalName else (asset_data.name.strip() if asset_data.name else "")
        ext = os.path.splitext(filename)[1].lower().lstrip('.')
        if ext and ext not in [t.lower() for t in all_tags]:
            all_tags.append(ext)

        filename_clean = filename.strip()
        if filename_clean and filename_clean.lower() not in [t.lower() for t in all_tags]:
            all_tags.append(filename_clean)

        # Automatically add the current year as a tag
        current_year = str(datetime.utcnow().year)
        if current_year not in [t.lower() for t in all_tags]:
            all_tags.append(current_year)

        if all_tags:
            for tag_name in all_tags:
                if tag_name.strip():
                    tag_objects.append(self.tag_service.get_or_create_tag(tag_name))
        
        # If active library folders exist, assign to matching or first active library folder
        active_folder = self.db.query(LibraryFolder).filter(LibraryFolder.is_active == True).first()
        folder_id = active_folder.id if active_folder else None

        creation_dict = {
            "name": asset_data.name.strip(),
            "original_name": asset_data.originalName.strip() if asset_data.originalName else asset_data.name.strip(),
            "mime_type": asset_data.mimeType.strip() if asset_data.mimeType else "application/octet-stream",
            "size_bytes": asset_data.sizeBytes if asset_data.sizeBytes is not None else 0,
            "storage_path": asset_data.storagePath if asset_data.storagePath else "",
            "description": asset_data.description if asset_data.description else None,
            "folder_id": folder_id,
            "tags": tag_objects
        }
        
        return self.asset_repo.create(creation_dict)

    async def upload_multipart_file(self, file: UploadFile, description: str = "", tags: List[str] = []) -> Asset:
        contents = await file.read()
        
        # Calculate SHA256 hash
        sha256_hash = hashlib.sha256(contents).hexdigest()
        
        # Generate UUID for disk storage filename
        file_uuid = str(uuid.uuid4())
        file_ext = os.path.splitext(file.filename)[1] if file.filename else ""
        disk_filename = f"{file_uuid}{file_ext}"
        
        # Resolve storage path dynamically relative to the backend root directory
        storage_dir = self._get_storage_dir()
        os.makedirs(storage_dir, exist_ok=True)
        storage_path = os.path.join(storage_dir, disk_filename)
        
        with open(storage_path, "wb") as f:
            f.write(contents)
            
        # Metadata parsing
        mime_type = file.content_type or "application/octet-stream"
        size_bytes = len(contents)
        
        # Optional Pillow Image processing
        if mime_type.startswith("image/"):
            try:
                img = Image.open(io.BytesIO(contents))
                width, height = img.size
                if not description:
                    description = f"Image dimensions: {width}x{height}"
                else:
                    description += f" (Dimensions: {width}x{height})"
            except Exception:
                pass
                
        # Handle tags
        tag_objects = []
        all_tags = list(tags) if tags else []
        filename = file.filename or ""
        base_name_raw, ext_with_dot = os.path.splitext(filename)
        ext = ext_with_dot.lower().lstrip('.')
        if ext and ext not in [t.lower() for t in all_tags]:
            all_tags.append(ext)

        filename_clean = filename.strip()
        if filename_clean and filename_clean.lower() not in [t.lower() for t in all_tags]:
            all_tags.append(filename_clean)

        # Automatically add the current year as a tag
        current_year = str(datetime.utcnow().year)
        if current_year not in [t.lower() for t in all_tags]:
            all_tags.append(current_year)

        for tag_name in all_tags:
            if tag_name.strip():
                tag_objects.append(self.tag_service.get_or_create_tag(tag_name))
                
        asset_name = file.filename if file.filename else "unnamed_asset"
        unique_asset_name = self._generate_unique_name(asset_name)

        creation_dict = {
            "id": file_uuid,
            "name": unique_asset_name,
            "original_name": asset_name,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "storage_path": f"storage/{disk_filename}",
            "description": description if description else f"SHA256: {sha256_hash}",
            "tags": tag_objects
        }
        
        return self.asset_repo.create(creation_dict)


    def is_protected_tag(self, asset: Asset, tag_name: str) -> bool:
        t_clean = tag_name.strip().lower()
        if not t_clean or not asset:
            return False

        names_to_check = [asset.name or "", asset.original_name or ""]
        for name in names_to_check:
            if not name:
                continue
            name_lower = name.lower()
            base_name, ext = os.path.splitext(name_lower)
            ext_clean = ext.lstrip('.')

            if t_clean == ext_clean:
                return True
            if t_clean == base_name:
                return True
            if t_clean == name_lower:
                return True

            t_norm = t_clean.replace('_', ' ').replace('-', ' ')
            base_norm = base_name.replace('_', ' ').replace('-', ' ')
            name_norm = name_lower.replace('_', ' ').replace('-', ' ')
            if t_norm == base_norm or t_norm == name_norm:
                return True

            base_no_dup = re.sub(r'\s*\(\d+\)$', '', base_name).strip()
            if base_no_dup:
                base_no_dup_norm = base_no_dup.replace('_', ' ').replace('-', ' ')
                if t_clean == base_no_dup or t_norm == base_no_dup_norm:
                    return True

        return False

    def update_asset(self, id: str, asset_update: AssetUpdate) -> Optional[Asset]:
        asset = self.asset_repo.find_by_id(id)
        if not asset:
            return None
            
        if asset_update.name is not None:
            asset.name = asset_update.name
            
        if asset_update.description is not None:
            asset.description = asset_update.description
            
        if asset_update.tags is not None:
            protected_tags = [t for t in asset.tags if self.is_protected_tag(asset, t.name)]
            protected_names = {t.name.lower() for t in protected_tags}
            
            tag_objects = list(protected_tags)
            for tag_name in asset_update.tags:
                if tag_name.strip() and tag_name.strip().lower() not in protected_names:
                    tag_objects.append(self.tag_service.get_or_create_tag(tag_name))
            asset.tags = tag_objects
            
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def batch_add_tags(self, asset_ids: List[str], tags: List[str]) -> int:
        clean_tags = [t.strip() for t in tags if t.strip()]
        if not clean_tags or not asset_ids:
            return 0
            
        tag_objects = [self.tag_service.get_or_create_tag(t) for t in clean_tags]
        updated_count = 0
        
        for asset_id in asset_ids:
            asset = self.asset_repo.find_by_id(asset_id)
            if not asset:
                continue
            existing_tag_ids = {t.id for t in asset.tags}
            added = False
            for tag_obj in tag_objects:
                if tag_obj.id not in existing_tag_ids:
                    asset.tags.append(tag_obj)
                    existing_tag_ids.add(tag_obj.id)
                    added = True
            if added:
                updated_count += 1
                
        self.db.commit()
        return updated_count

    def batch_remove_tags(self, asset_ids: List[str], tags: List[str]) -> int:
        clean_tags = [t.strip().lower() for t in tags if t.strip()]
        if not asset_ids:
            return 0
            
        updated_count = 0
        for asset_id in asset_ids:
            asset = self.asset_repo.find_by_id(asset_id)
            if not asset:
                continue
            
            if not clean_tags:
                initial_count = len(asset.tags)
                asset.tags = [t for t in asset.tags if self.is_protected_tag(asset, t.name)]
                if len(asset.tags) < initial_count:
                    updated_count += 1
            else:
                initial_count = len(asset.tags)
                asset.tags = [
                    t for t in asset.tags
                    if t.name.lower() not in clean_tags or self.is_protected_tag(asset, t.name)
                ]
                if len(asset.tags) < initial_count:
                    updated_count += 1
                    
        self.db.commit()
        return updated_count

    def batch_replace_tag(self, asset_ids: List[str], old_tag: str, new_tag: str) -> int:
        old_clean = old_tag.strip().lower()
        new_clean = new_tag.strip()
        if not old_clean or not new_clean or not asset_ids:
            return 0
            
        new_tag_obj = self.tag_service.get_or_create_tag(new_clean)
        updated_count = 0
        
        for asset_id in asset_ids:
            asset = self.asset_repo.find_by_id(asset_id)
            if not asset:
                continue
            
            if self.is_protected_tag(asset, old_tag):
                continue

            has_old = any(t.name.lower() == old_clean for t in asset.tags)
            if has_old:
                filtered_tags = [t for t in asset.tags if t.name.lower() != old_clean]
                if not any(t.id == new_tag_obj.id for t in filtered_tags):
                    filtered_tags.append(new_tag_obj)
                asset.tags = filtered_tags
                updated_count += 1
                
        self.db.commit()
        return updated_count



    def batch_set_tags(self, asset_ids: List[str], tags: List[str]) -> int:
        clean_tags = [t.strip() for t in tags if t.strip()]
        tag_objects = [self.tag_service.get_or_create_tag(t) for t in clean_tags]
        updated_count = 0
        
        for asset_id in asset_ids:
            asset = self.asset_repo.find_by_id(asset_id)
            if not asset:
                continue
            protected_tags = [t for t in asset.tags if self.is_protected_tag(asset, t.name)]
            protected_names = {t.name.lower() for t in protected_tags}
            
            final_tags = list(protected_tags)
            for t_obj in tag_objects:
                if t_obj.name.lower() not in protected_names:
                    final_tags.append(t_obj)
            asset.tags = final_tags
            updated_count += 1
            
        self.db.commit()
        return updated_count



    def search_assets(self, query: str) -> List[Asset]:
        term = f"%{query.strip().lower()}%"
        return self.db.query(Asset).filter(
            or_(
                Asset.name.ilike(term),
                Asset.original_name.ilike(term),
                Asset.description.ilike(term),
                Asset.tags.any(Tag.name.ilike(term))
            )
        ).all()


    def get_inventory(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        search: str = "",
        tags: Optional[Union[List[str], str]] = None,
        folder_id: Optional[str] = None,
        subfolder_path: Optional[str] = None,
        path_prefix: Optional[str] = None
    ) -> dict:
        query = self.db.query(Asset)

        # Check active library folders
        active_folders = self.db.query(LibraryFolder).filter(LibraryFolder.is_active == True).all()
        active_folder_ids = [f.id for f in active_folders]

        if not active_folder_ids:
            # If no library folders exist in the system, return empty list
            return {
                "items": [],
                "total": 0,
                "page": page,
                "pageSize": page_size,
                "totalPages": 0
            }

        if folder_id and folder_id.strip():
            query = query.filter(Asset.folder_id == folder_id.strip())
        else:
            # When viewing All Assets, only return assets belonging to active library folders
            query = query.filter(Asset.folder_id.in_(active_folder_ids))

        filter_path = subfolder_path or path_prefix
        if filter_path and filter_path.strip():
            norm_filter_path = os.path.normpath(filter_path.strip())
            query = query.filter(
                or_(
                    Asset.storage_path == norm_filter_path,
                    Asset.storage_path.startswith(norm_filter_path + os.sep),
                    Asset.storage_path.startswith(norm_filter_path + "/")
                )
            )

        if search.strip():
            term = f"%{search.strip().lower()}%"
            query = query.filter(
                or_(
                    Asset.name.ilike(term),
                    Asset.original_name.ilike(term),
                    Asset.description.ilike(term),
                    Asset.tags.any(Tag.name.ilike(term))
                )
            )

        if tags:
            tag_inputs = tags if isinstance(tags, list) else [tags]
            tag_list = []
            for item in tag_inputs:
                if item:
                    for sub in str(item).split(","):
                        t_clean = sub.strip()
                        if t_clean:
                            tag_list.append(t_clean)
            tag_list = list(set(tag_list))
            for tag_name in tag_list:
                clean_tag = tag_name.lstrip("#")
                query = query.filter(
                    Asset.tags.any(
                        or_(
                            Tag.name.ilike(clean_tag),
                            Tag.name.ilike(f"#{clean_tag}")
                        )
                    )
                )

            
        total = query.count()
        
        col = getattr(Asset, sort_by, Asset.created_at)
        if sort_dir.lower() == "asc":
            query = query.order_by(asc(col))
        else:
            query = query.order_by(desc(col))
            
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()
        
        total_pages = max(1, math.ceil(total / page_size))
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "pageSize": page_size,
            "totalPages": total_pages
        }

    def purge_all_assets(self) -> int:
        assets = self.asset_repo.find_all()
        count = 0
        storage_dir = self._get_storage_dir()

        for asset in assets:
            abs_file_path = os.path.abspath(os.path.join(storage_dir, os.path.basename(asset.storage_path)))
            self.asset_repo.delete(asset.id)
            if asset.storage_path and os.path.exists(abs_file_path):
                try:
                    os.remove(abs_file_path)
                except OSError as exc:
                    logging.getLogger("assetvault").warning(
                        "Could not remove file %s during purge: %s", abs_file_path, exc
                    )
            count += 1
        return count

    def create_backup_zip(self, output_path: str):
        from app.config import settings
        storage_dir = self._get_storage_dir()
        db_file = os.path.abspath(settings.database_url.replace("sqlite:///", ""))
        
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # 1. Add database file if it exists
            if os.path.exists(db_file):
                zip_file.write(db_file, arcname="backend/db/assetvault.sqlite")
                
            # 2. Add storage files
            if os.path.exists(storage_dir):
                for root, _, files in os.walk(storage_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Avoid zipping the backup zip file itself if it's placed in storage/
                        if os.path.abspath(file_path) == os.path.abspath(output_path):
                            continue
                        rel_path = os.path.join("storage", os.path.relpath(file_path, storage_dir))
                        zip_file.write(file_path, arcname=rel_path)

    def create_assets_zip(self, asset_ids: List[str], zip_path: str) -> None:
        storage_dir = self._get_storage_dir()
        
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for asset_id in asset_ids:
                asset = self.asset_repo.find_by_id(asset_id)
                if not asset or not asset.storage_path:
                    continue
                abs_file_path = os.path.abspath(os.path.join(storage_dir, os.path.basename(asset.storage_path)))
                if os.path.exists(abs_file_path):
                    arcname = asset.original_name or asset.name
                    base_name, ext = os.path.splitext(arcname)
                    counter = 1
                    while arcname in zip_file.namelist():
                        arcname = f"{base_name} ({counter}){ext}"
                        counter += 1
                    zip_file.write(abs_file_path, arcname)

    def restore_from_backup_zip(self, zip_bytes: bytes) -> int:
        import tempfile
        import shutil
        
        from app.config import settings
        storage_dir = self._get_storage_dir()
        db_file = os.path.abspath(settings.database_url.replace("sqlite:///", ""))
        
        os.makedirs(storage_dir, exist_ok=True)
        # Create a temp directory inside storage_dir to keep it inside the workspace
        temp_extract_dir = tempfile.mkdtemp(dir=storage_dir)
        try:
            # Extract the zip file contents
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zip_ref:
                zip_ref.extractall(temp_extract_dir)
            
            # 1. Validate the extracted contents
            extracted_db = os.path.join(temp_extract_dir, "backend", "db", "assetvault.sqlite")
            if not os.path.exists(extracted_db):
                raise ValueError("Invalid backup ZIP: missing backend/db/assetvault.sqlite")
                
            # 2. Close active database connections
            self.db.close()
            from app.db.session import engine
            engine.dispose()
            
            # 3. Overwrite the database file
            db_dir = os.path.dirname(db_file)
            os.makedirs(db_dir, exist_ok=True)
            shutil.copy2(extracted_db, db_file)
            
            # 4. Clear existing storage files
            for filename in os.listdir(storage_dir):
                file_path = os.path.join(storage_dir, filename)
                # Skip the temporary extraction directory
                if os.path.abspath(file_path) == os.path.abspath(temp_extract_dir):
                    continue
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    logging.getLogger("assetvault").error("Failed to delete %s during restore: %s", file_path, e)
                    
            # 5. Restore files to storage directory
            extracted_storage = os.path.join(temp_extract_dir, "storage")
            if os.path.exists(extracted_storage):
                for filename in os.listdir(extracted_storage):
                    src = os.path.join(extracted_storage, filename)
                    dst = os.path.join(storage_dir, filename)
                    shutil.copy2(src, dst)
                    
            # 6. Count restored assets from the new database
            from app.db.session import SessionLocal
            from app.repositories.asset_repository import AssetRepository
            new_db = SessionLocal()
            try:
                new_repo = AssetRepository(new_db)
                count = len(new_repo.find_all())
            finally:
                new_db.close()
                
            return count
        finally:
            # Clean up the temp extract directory
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)

    def generate_assets_csv(self) -> str:
        assets = self.asset_repo.find_all()
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        
        # Write header
        writer.writerow([
            "ID", "Name", "Original Name", "Mime Type", "Size Bytes", 
            "Storage Path", "Description", "Created At", "Tags"
        ])
        
        # Write rows
        for asset in assets:
            tag_names = [t.name for t in asset.tags]
            tags_str = ", ".join(tag_names)
            writer.writerow([
                asset.id,
                asset.name,
                asset.original_name,
                asset.mime_type,
                asset.size_bytes,
                asset.storage_path,
                asset.description or "",
                asset.created_at.isoformat() if asset.created_at else "",
                tags_str
            ])
            
        return output.getvalue()

    def restore_assets_from_csv(self, csv_content: str) -> int:
        import csv
        from datetime import datetime
        
        f = io.StringIO(csv_content)
        reader = csv.reader(f)
        
        # Read header and verify it's the expected structure
        try:
            header = next(reader)
        except StopIteration:
            raise ValueError("CSV file is empty")
            
        # Allow checking if the main columns exist
        if not all(col in header for col in ["ID", "Name", "Storage Path"]):
            raise ValueError("CSV header is invalid. Required columns: ID, Name, Storage Path")
            
        # Get column indices
        idx_id = header.index("ID")
        idx_name = header.index("Name")
        idx_orig = header.index("Original Name") if "Original Name" in header else -1
        idx_mime = header.index("Mime Type") if "Mime Type" in header else -1
        idx_size = header.index("Size Bytes") if "Size Bytes" in header else -1
        idx_path = header.index("Storage Path") if "Storage Path" in header else -1
        idx_desc = header.index("Description") if "Description" in header else -1
        idx_date = header.index("Created At") if "Created At" in header else -1
        idx_tags = header.index("Tags") if "Tags" in header else -1
        
        count = 0
        for row in reader:
            if not row or len(row) <= max(idx_id, idx_name, idx_path):
                continue
                
            asset_id = row[idx_id].strip()
            name = row[idx_name].strip()
            storage_path = row[idx_path].strip()
            
            if not asset_id or not name:
                continue
                
            original_name = row[idx_orig].strip() if idx_orig != -1 else name
            mime_type = row[idx_mime].strip() if idx_mime != -1 else "application/octet-stream"
            
            try:
                size_bytes = int(row[idx_size].strip()) if idx_size != -1 else 0
            except ValueError:
                size_bytes = 0
                
            description = row[idx_desc].strip() if idx_desc != -1 else None
            if description == "":
                description = None
                
            created_at = None
            if idx_date != -1:
                date_str = row[idx_date].strip()
                if date_str:
                    try:
                        created_at = datetime.fromisoformat(date_str)
                    except ValueError:
                        pass
            if not created_at:
                created_at = datetime.utcnow()
                
            # Process tags
            tag_objects = []
            if idx_tags != -1:
                tags_str = row[idx_tags].strip()
                if tags_str:
                    tag_names = [t.strip() for t in tags_str.split(",") if t.strip()]
                    for tag_name in tag_names:
                        tag_objects.append(self.tag_service.get_or_create_tag(tag_name))
                        
            # Upsert
            asset = self.asset_repo.find_by_id(asset_id)
            if asset:
                # Update
                asset.name = name
                asset.original_name = original_name
                asset.mime_type = mime_type
                asset.size_bytes = size_bytes
                asset.storage_path = storage_path
                asset.description = description
                asset.created_at = created_at
                asset.tags = tag_objects
                self.db.commit()
                self.db.refresh(asset)
            else:
                # Create new
                creation_dict = {
                    "id": asset_id,
                    "name": name,
                    "original_name": original_name,
                    "mime_type": mime_type,
                    "size_bytes": size_bytes,
                    "storage_path": storage_path,
                    "description": description,
                    "created_at": created_at,
                    "tags": tag_objects
                }
                self.asset_repo.create(creation_dict)
                
            count += 1
            
        return count

    def verify_assets_integrity(self) -> str:
        from datetime import datetime
        assets = self.asset_repo.find_all()
        storage_dir = self._get_storage_dir()
        
        log_lines = []
        log_lines.append("==================================================")
        log_lines.append("           ASSETVAULT INTEGRITY REPORT           ")
        log_lines.append(f" Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log_lines.append("==================================================")
        log_lines.append("")
        
        total_count = len(assets)
        missing_count = 0
        found_count = 0
        details = []
        
        for asset in assets:
            abs_path = os.path.abspath(os.path.join(storage_dir, os.path.basename(asset.storage_path))) if asset.storage_path else ""
            exists = False
            if abs_path and os.path.exists(abs_path):
                exists = True
                found_count += 1
            else:
                exists = False
                missing_count += 1
                
            status_str = "OK" if exists else "MISSING"
            details.append(f"[{status_str}] ID: {asset.id}")
            details.append(f"      Name: {asset.name}")
            details.append(f"      Path: {abs_path or 'No path defined'}")
            details.append(f"      Size: {asset.size_bytes or 0} bytes")
            details.append("")
            
        log_lines.append(f"Summary:")
        log_lines.append(f"  Total Assets Registered: {total_count}")
        log_lines.append(f"  Files Existing on Disk : {found_count}")
        log_lines.append(f"  Files Missing on Disk  : {missing_count}")
        log_lines.append("")
        log_lines.append("--------------------------------------------------")
        log_lines.append("Detailed Logs:")
        log_lines.append("--------------------------------------------------")
        log_lines.append("")
        log_lines.extend(details)
        log_lines.append("==================================================")
        log_lines.append("             END OF INTEGRITY REPORT              ")
        log_lines.append("==================================================")
        
        return "\n".join(log_lines)

    def scan_and_import_untracked_files(self) -> dict:
        import uuid
        import mimetypes
        import hashlib
        
        # 1. Resolve paths
        storage_dir = self._get_storage_dir()
        
        if not os.path.exists(storage_dir):
            return {"scanned": 0, "imported": 0, "errors": []}
            
        # 2. Get all registered storage paths in the database
        assets = self.asset_repo.find_all()
        registered_filenames = set()
        for asset in assets:
            if asset.storage_path:
                basename = os.path.basename(asset.storage_path)
                registered_filenames.add(basename.lower())
                
        # 3. Scan the storage directory for untracked files
        scanned_count = 0
        imported_count = 0
        errors = []
        
        for filename in os.listdir(storage_dir):
            file_path = os.path.join(storage_dir, filename)
            
            if not os.path.isfile(file_path):
                continue
                
            scanned_count += 1
            
            if filename.lower() in registered_filenames:
                continue
                
            # Found untracked file! Let's import it
            try:
                with open(file_path, "rb") as f:
                    contents = f.read()
                
                size_bytes = len(contents)
                sha256_hash = hashlib.sha256(contents).hexdigest()
                
                name_without_ext, ext_with_dot = os.path.splitext(filename)
                ext = ext_with_dot.lower().lstrip('.')
                
                is_valid_uuid = False
                try:
                    uuid.UUID(name_without_ext)
                    is_valid_uuid = True
                except ValueError:
                    pass
                    
                if is_valid_uuid:
                    file_uuid = name_without_ext
                    final_filename = filename
                    final_storage_path = f"storage/{final_filename}"
                else:
                    file_uuid = str(uuid.uuid4())
                    final_filename = f"{file_uuid}{ext_with_dot.lower()}"
                    final_storage_path = f"storage/{final_filename}"
                    new_file_path = os.path.join(storage_dir, final_filename)
                    
                    os.rename(file_path, new_file_path)
                    file_path = new_file_path
                    
                tag_objects = []
                all_tags = []
                if ext:
                    all_tags.append(ext)
                filename_clean = filename.strip()
                if filename_clean and filename_clean.lower() not in [t.lower() for t in all_tags]:
                    all_tags.append(filename_clean)
                current_year = str(datetime.utcnow().year)
                if current_year not in [t.lower() for t in all_tags]:
                    all_tags.append(current_year)

                for tag_name in all_tags:
                    if tag_name.strip():
                        tag_objects.append(self.tag_service.get_or_create_tag(tag_name))
                    
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type:
                    mime_type = "application/octet-stream"
                    
                unique_asset_name = self._generate_unique_name(filename)

                creation_dict = {
                    "id": file_uuid,
                    "name": unique_asset_name,
                    "original_name": filename,
                    "mime_type": mime_type,
                    "size_bytes": size_bytes,
                    "storage_path": final_storage_path,
                    "description": f"Imported from untracked storage file (SHA256: {sha256_hash})",
                    "tags": tag_objects
                }
                
                self.asset_repo.create(creation_dict)
                imported_count += 1
                registered_filenames.add(final_filename.lower())
                
            except Exception as e:
                errors.append(f"Failed to import {filename}: {str(e)}")
                
        return {
            "scanned": scanned_count,
            "imported": imported_count,
            "errors": errors
        }






from pydantic import BaseModel, computed_field, model_validator
from datetime import datetime
from typing import List, Optional, Any
import os
import sys
from app.schemas.tag import TagResponse

class AssetCreate(BaseModel):
    name: str
    originalName: Optional[str] = None
    mimeType: Optional[str] = None
    sizeBytes: Optional[int] = None
    storagePath: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    folderId: Optional[str] = None
    fileModifiedAt: Optional[datetime] = None

class AssetResponse(BaseModel):
    id: str
    name: str
    original_name: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    storage_path: Optional[str] = None
    description: Optional[str] = None
    folder_id: Optional[str] = None
    file_modified_at: Optional[datetime] = None
    thumbnail_path: Optional[str] = None
    created_at: datetime
    tags: List[TagResponse] = []

    @computed_field
    @property
    def absolute_path(self) -> str:
        if not self.storage_path:
            return ""
        
        # If storage_path is already an absolute path or exists directly on disk
        if os.path.isabs(self.storage_path) or os.path.exists(self.storage_path):
            return os.path.abspath(self.storage_path)
        
        # Resolve settings.json path for managed internal storage
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            settings_path = os.path.abspath(os.path.join(exe_dir, "db", "settings.json"))
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            settings_path = os.path.abspath(os.path.join(current_dir, "..", "..", "db", "settings.json"))
            
        storage_dir = ""
        if os.path.exists(settings_path):
            try:
                import json
                with open(settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    custom_dir = data.get("storage_dir")
                    if custom_dir:
                        storage_dir = os.path.abspath(custom_dir)
            except Exception:
                pass
                
        if not storage_dir:
            if getattr(sys, "frozen", False):
                exe_dir = os.path.dirname(sys.executable)
                storage_dir = os.path.abspath(os.path.join(exe_dir, "storage"))
            else:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                storage_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "..", "storage"))
                
        filename = os.path.basename(self.storage_path)
        return os.path.abspath(os.path.join(storage_dir, filename))

    class Config:
        from_attributes = True

class AssetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None

class BatchTagRequest(BaseModel):
    asset_ids: List[str]
    tags: List[str]

class BatchTagReplaceRequest(BaseModel):
    asset_ids: List[str]
    old_tag: str
    new_tag: str

# Explorer & File Management Schemas
class RevealRequest(BaseModel):
    asset_id: Optional[str] = None
    folder_id: Optional[str] = None
    raw_path: Optional[str] = None
    path: Optional[str] = None

class RenameRequest(BaseModel):
    asset_id: Optional[str] = None
    path: Optional[str] = None
    new_name: str

class TrashRequest(BaseModel):
    asset_id: Optional[str] = None
    asset_ids: Optional[List[str]] = None
    path: Optional[str] = None
    paths: Optional[List[str]] = None

class BatchTrashRequest(BaseModel):
    asset_ids: Optional[List[str]] = None
    paths: Optional[List[str]] = None

class RenameItem(BaseModel):
    asset_id: str
    new_name: str

class BatchRenameRequest(BaseModel):
    renames: Optional[List[RenameItem]] = None
    asset_ids: Optional[List[str]] = None
    pattern: Optional[str] = None  # e.g., "prefix_{name}_suffix"
    prefix: Optional[str] = None
    suffix: Optional[str] = None

class BatchMoveRequest(BaseModel):
    asset_ids: List[str]
    destination_folder: str = ""
    destination_directory: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def resolve_destination(cls, data: Any) -> Any:
        if isinstance(data, dict):
            dest = data.get("destination_folder") or data.get("destination_directory") or data.get("destinationFolder") or data.get("destinationDirectory")
            if not dest or not str(dest).strip().strip('"').strip("'"):
                raise ValueError("destination_folder is required.")
            data["destination_folder"] = str(dest).strip().strip('"').strip("'")
        return data

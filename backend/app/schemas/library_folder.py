from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class LibraryFolderCreate(BaseModel):
    path: str
    name: Optional[str] = None
    is_recursive: bool = True
    auto_tag_folder: bool = True
    custom_tags: Optional[List[str]] = None

class LibraryFolderUpdate(BaseModel):
    name: Optional[str] = None
    is_recursive: Optional[bool] = None
    auto_tag_folder: Optional[bool] = None
    custom_tags: Optional[List[str]] = None
    is_active: Optional[bool] = None

class LibraryFolderResponse(BaseModel):
    id: str
    path: str
    name: str
    is_recursive: bool
    auto_tag_folder: bool
    custom_tags: Optional[str] = None
    is_active: bool
    asset_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True

class FolderTreeNode(BaseModel):
    name: str
    path: str
    relative_path: str
    asset_count: int = 0
    children: List['FolderTreeNode'] = []

FolderTreeNode.model_rebuild()

class FolderScanResult(BaseModel):
    folder_id: str
    folder_path: str
    total_scanned: int
    newly_indexed: int
    already_indexed: int
    errors: List[str] = []

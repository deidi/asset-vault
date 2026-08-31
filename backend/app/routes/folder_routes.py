from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.services.folder_service import FolderService
from app.schemas.library_folder import (
    LibraryFolderCreate,
    LibraryFolderUpdate,
    LibraryFolderResponse,
    FolderScanResult,
    FolderTreeNode
)

router = APIRouter(prefix="/folders", tags=["Folders"])

@router.post("", response_model=LibraryFolderResponse, status_code=status.HTTP_201_CREATED)
def create_library_folder(payload: LibraryFolderCreate, db: Session = Depends(get_db)) -> LibraryFolderResponse:
    service = FolderService(db)
    try:
        return service.add_folder(payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("", response_model=List[LibraryFolderResponse])
def get_library_folders(active_only: bool = False, db: Session = Depends(get_db)) -> List[LibraryFolderResponse]:
    service = FolderService(db)
    return service.list_folders(active_only=active_only)

@router.get("/{folder_id}", response_model=LibraryFolderResponse)
def get_library_folder(folder_id: str, db: Session = Depends(get_db)) -> LibraryFolderResponse:
    service = FolderService(db)
    folder = service.get_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return folder

@router.patch("/{folder_id}", response_model=LibraryFolderResponse)
def update_library_folder(folder_id: str, payload: LibraryFolderUpdate, db: Session = Depends(get_db)) -> LibraryFolderResponse:
    service = FolderService(db)
    try:
        return service.update_folder(folder_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.delete("/{folder_id}", status_code=status.HTTP_200_OK)
def delete_library_folder(folder_id: str, db: Session = Depends(get_db)) -> dict:
    service = FolderService(db)
    success = service.delete_folder(folder_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return {"status": "success", "deleted_folder_id": folder_id}

@router.get("/{folder_id}/tree", response_model=FolderTreeNode)
def get_library_folder_tree(folder_id: str, db: Session = Depends(get_db)) -> FolderTreeNode:
    service = FolderService(db)
    try:
        return service.get_folder_tree(folder_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{folder_id}/scan", response_model=FolderScanResult)
def scan_library_folder(folder_id: str, db: Session = Depends(get_db)) -> FolderScanResult:
    service = FolderService(db)
    try:
        return service.scan_folder(folder_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/scan-all", response_model=List[FolderScanResult])
def scan_all_library_folders(db: Session = Depends(get_db)) -> List[FolderScanResult]:
    service = FolderService(db)
    return service.scan_all_active_folders()

@router.post("/picker", status_code=status.HTTP_200_OK)
def open_folder_picker(db: Session = Depends(get_db)) -> dict:
    service = FolderService(db)
    selected_path = service.open_folder_picker_dialog()
    return {"selected_path": selected_path}

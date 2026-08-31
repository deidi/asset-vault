from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.db.session import get_db
from app.services.explorer_service import ExplorerService
from app.schemas.asset import (
    RevealRequest,
    RenameRequest,
    TrashRequest,
    BatchTrashRequest,
    BatchMoveRequest,
    AssetResponse
)

router = APIRouter(prefix="/explorer", tags=["Explorer"])

@router.post("/reveal", status_code=status.HTTP_200_OK)
def reveal_in_explorer(payload: RevealRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    service = ExplorerService(db)
    result = service.reveal_in_explorer(
        target_path=payload.path or payload.raw_path,
        asset_id=payload.asset_id,
        folder_id=payload.folder_id
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("message"))
    return result

@router.post("/rename", response_model=AssetResponse, status_code=status.HTTP_200_OK)
def rename_asset_on_disk(payload: RenameRequest, db: Session = Depends(get_db)) -> AssetResponse:
    service = ExplorerService(db)
    if not payload.asset_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="asset_id is required for renaming.")
    try:
        asset = service.rename_on_disk(asset_id=payload.asset_id, new_name=payload.new_name)
        return AssetResponse.model_validate(asset)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (FileNotFoundError, FileExistsError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/trash", status_code=status.HTTP_200_OK)
def trash_asset_to_recycle_bin(payload: TrashRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    service = ExplorerService(db)
    if payload.asset_ids and len(payload.asset_ids) > 0:
        return service.batch_trash(asset_ids=payload.asset_ids)
    if payload.asset_id:
        try:
            return service.trash_to_recycle_bin(asset_id=payload.asset_id)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="asset_id or asset_ids is required for trashing.")

@router.post("/batch-trash", status_code=status.HTTP_200_OK)
def batch_trash_assets(payload: BatchTrashRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    service = ExplorerService(db)
    asset_ids = payload.asset_ids or []
    if not asset_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="asset_ids list cannot be empty.")
    return service.batch_trash(asset_ids=asset_ids)

@router.post("/batch-move", status_code=status.HTTP_200_OK)
def batch_move_assets(payload: BatchMoveRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    if not payload.asset_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="asset_ids list cannot be empty.")
    service = ExplorerService(db)
    return service.batch_move(asset_ids=payload.asset_ids, destination_folder=payload.destination_folder)

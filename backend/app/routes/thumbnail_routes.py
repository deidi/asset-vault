import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from app.db.session import get_db
from app.models.asset import Asset
from app.repositories.asset_repository import AssetRepository
from app.services.thumbnail_service import thumbnail_service
from app.services.folder_service import FolderService

logger = logging.getLogger("assetvault.thumbnail_routes")

router = APIRouter(tags=["Thumbnails & Cache"])

@router.get("/assets/{asset_id}/thumbnail")
def get_asset_thumbnail(
    asset_id: str,
    width: int = Query(default=350, ge=50, le=1200),
    height: int = Query(default=350, ge=50, le=1200),
    db: Session = Depends(get_db)
):
    """Returns an optimized WebP thumbnail for the specified asset."""
    thumbnail_path = thumbnail_service.get_or_generate_thumbnail(
        db=db,
        asset_id=asset_id,
        width=width,
        height=height
    )
    if not thumbnail_path or not os.path.exists(thumbnail_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thumbnail not available for asset {asset_id}"
        )

    return FileResponse(
        path=thumbnail_path,
        media_type="image/webp",
        headers={"Cache-Control": "public, max-age=86400"}
    )

@router.get("/cache/stats", status_code=status.HTTP_200_OK)
def get_cache_statistics() -> Dict[str, Any]:
    """Returns current disk usage and file count of the thumbnail cache."""
    return thumbnail_service.get_cache_stats()

@router.post("/cache/clear", status_code=status.HTTP_200_OK)
def clear_thumbnail_cache(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Flushes all generated WebP thumbnails from disk and resets database cache references."""
    return thumbnail_service.clear_all_cache(db=db)

@router.post("/library/rescan", status_code=status.HTTP_200_OK)
def rescan_library_and_fix_cache(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Full maintenance routine:
    1. Flushes the thumbnail cache to fix any stale/corrupted thumbnails.
    2. Purges database records for any files that no longer exist on disk.
    3. Re-scans all active library folders to index any newly added media.
    """
    # 1. Clear cache
    cache_result = thumbnail_service.clear_all_cache(db=db)

    # 2. Purge stale records
    asset_repo = AssetRepository(db)
    all_assets = asset_repo.find_all()
    purged_missing_count = 0
    
    for asset in all_assets:
        if asset.storage_path:
            norm_path = os.path.normpath(asset.storage_path)
            # If in-place file no longer exists on disk, remove from index
            if not os.path.exists(norm_path):
                asset_repo.delete(asset.id)
                purged_missing_count += 1

    # 3. Rescan all active library folders
    folder_service = FolderService(db)
    scan_results = folder_service.scan_all_active_folders()

    total_scanned = sum(r.total_scanned for r in scan_results)
    newly_indexed = sum(r.newly_indexed for r in scan_results)
    already_indexed = sum(r.already_indexed for r in scan_results)

    return {
        "status": "success",
        "cache_cleared": cache_result,
        "purged_missing_files": purged_missing_count,
        "total_scanned": total_scanned,
        "newly_indexed": newly_indexed,
        "already_indexed": already_indexed,
        "folder_results": [r.model_dump() for r in scan_results]
    }

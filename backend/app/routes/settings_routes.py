import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict

from app.db.session import get_db
from app.models.asset import Asset
from app.services.category_service import CategoryService
from app.schemas.settings import (
    FileTypeSettingsResponse,
    UpdateFileTypeSettingsRequest,
    UpdateFileTypeSettingsResponse,
    ResetFileTypeSettingsRequest
)

logger = logging.getLogger("assetvault.settings_routes")

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("/file-types", response_model=FileTypeSettingsResponse)
def get_file_type_settings(db: Session = Depends(get_db)) -> FileTypeSettingsResponse:
    """Retrieves active category extensions, factory defaults, and current catalog asset counts."""
    categories = CategoryService.get_extensions_map()
    defaults = CategoryService.get_default_extensions_map()

    # Calculate real-time counts from database
    counts: Dict[str, int] = {
        "all": 0,
        "image": 0,
        "video": 0,
        "audio": 0,
        "document": 0,
        "other": 0
    }

    try:
        rows = db.query(Asset.category, func.count(Asset.id)).group_by(Asset.category).all()
        total = 0
        for cat, count in rows:
            clean_cat = cat or "other"
            counts[clean_cat] = count
            total += count
        counts["all"] = total
    except Exception as e:
        logger.warning(f"Failed to query category counts: {e}")

    return FileTypeSettingsResponse(
        categories=categories,
        defaults=defaults,
        counts=counts
    )

@router.put("/file-types", response_model=UpdateFileTypeSettingsResponse)
def update_file_type_settings(
    payload: UpdateFileTypeSettingsRequest,
    db: Session = Depends(get_db)
) -> UpdateFileTypeSettingsResponse:
    """Updates category extension mappings, persists them, and optionally re-categorizes existing assets."""
    try:
        updated_map, recat_count = CategoryService.save_extensions(
            categories=payload.categories,
            recategorize_existing=payload.recategorize_existing,
            db=db
        )
        return UpdateFileTypeSettingsResponse(
            status="success",
            categories=updated_map,
            recategorized_count=recat_count
        )
    except Exception as e:
        logger.error(f"Failed to update file type settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save settings: {str(e)}"
        )

@router.post("/file-types/reset", response_model=UpdateFileTypeSettingsResponse)
def reset_file_type_settings(
    payload: ResetFileTypeSettingsRequest,
    db: Session = Depends(get_db)
) -> UpdateFileTypeSettingsResponse:
    """Resets category extension mappings to defaults and optionally re-categorizes existing assets."""
    try:
        default_map, recat_count = CategoryService.reset_to_defaults(
            recategorize_existing=payload.recategorize_existing,
            db=db
        )
        return UpdateFileTypeSettingsResponse(
            status="success",
            categories=default_map,
            recategorized_count=recat_count
        )
    except Exception as e:
        logger.error(f"Failed to reset file type settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset settings: {str(e)}"
        )

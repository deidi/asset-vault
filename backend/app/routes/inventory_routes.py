from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.asset_service import AssetService
from app.schemas.asset import AssetResponse
from pydantic import BaseModel, computed_field
from typing import List, Optional

router = APIRouter()

class InventoryResponse(BaseModel):
    items: List[AssetResponse]
    total: int
    page: int
    pageSize: int
    totalPages: int

    @computed_field
    @property
    def assets(self) -> List[AssetResponse]:
        return self.items

@router.get("/inventory", response_model=InventoryResponse)
def get_inventory(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    sortBy: str = Query("created_at"),
    sortDir: str = Query("desc"),
    search: str = Query(""),
    db: Session = Depends(get_db)
):
    asset_service = AssetService(db)
    db_sort_by = sortBy
    if sortBy == "size":
         db_sort_by = "size_bytes"
    return asset_service.get_inventory(
        page=page,
        page_size=pageSize,
        sort_by=db_sort_by,
        sort_dir=sortDir,
        search=search
    )

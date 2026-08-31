import os
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.asset import AssetCreate, AssetResponse, AssetUpdate, BatchTagRequest, BatchTagReplaceRequest
from app.schemas.tag import TagCreate, TagResponse
from app.services.asset_service import AssetService
from app.services.tag_service import TagService
from app.routes.inventory_routes import InventoryResponse
from pydantic import BaseModel
from app.config import settings
from typing import List, Optional

router = APIRouter()

class DeleteRequest(BaseModel):
    id: str

@router.get("/files", response_model=List[AssetResponse])
def get_assets(db: Session = Depends(get_db)):
    asset_service = AssetService(db)
    return asset_service.get_all_assets()

@router.get("/file/{id}", response_model=AssetResponse)
def get_asset(id: str, db: Session = Depends(get_db)):
    asset_service = AssetService(db)
    asset = asset_service.get_asset_by_id(id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset

@router.post("/upload", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    request: Request,
    db: Session = Depends(get_db)
):
    content_type = request.headers.get("content-type", "")
    asset_service = AssetService(db)
    
    if "multipart/form-data" in content_type:
        try:
            form = await request.form()
            file = form.get("file")
            if not file or not hasattr(file, "filename"):
                raise HTTPException(status_code=400, detail="No file found in form data")
            
            description = form.get("description", "")
            if not isinstance(description, str):
                description = ""
                
            tags_str = form.get("tags", "")
            tags = []
            if tags_str and isinstance(tags_str, str):
                tags = [t.strip() for t in tags_str.split(",") if t.strip()]
                
            return await asset_service.upload_multipart_file(file, description, tags)
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=str(e))
    else:
        try:
            body = await request.json()
            asset_data = AssetCreate(**body)
            return asset_service.upload_asset(asset_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

@router.post("/tags", response_model=TagResponse)
def create_tag(tag_data: TagCreate, db: Session = Depends(get_db)):
    tag_service = TagService(db)
    try:
        return tag_service.get_or_create_tag(tag_data.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tags", response_model=List[TagResponse])
def get_tags(db: Session = Depends(get_db)):
    tag_service = TagService(db)
    return tag_service.get_all_tags()

@router.delete("/tags/unused")
def delete_unused_tags_endpoint(db: Session = Depends(get_db)):
    tag_service = TagService(db)
    deleted_count = tag_service.delete_unused_tags()
    return {"deleted_count": deleted_count, "message": f"Deleted {deleted_count} unused tag(s)"}

@router.delete("/tag/{id}")
def delete_tag(id: str, db: Session = Depends(get_db)):
    tag_service = TagService(db)
    deleted = tag_service.delete_tag(id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tag not found")
    return {"deleted": True}

@router.put("/tag/{id}", response_model=TagResponse)
def update_tag_endpoint(id: str, tag_data: TagCreate, db: Session = Depends(get_db)):
    tag_service = TagService(db)
    try:
        updated = tag_service.update_tag(id, tag_data.name)
        if not updated:
            raise HTTPException(status_code=404, detail="Tag not found")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=List[AssetResponse])
def search_assets(q: str, db: Session = Depends(get_db)):
    asset_service = AssetService(db)
    return asset_service.search_assets(q)

@router.delete("/file")
def delete_asset(req_body: DeleteRequest, db: Session = Depends(get_db)):
    asset_service = AssetService(db)
    deleted = asset_service.delete_asset(req_body.id)
    return {"deleted": deleted}

# 🚀 ASSET INVENTORY PAGINATED & FILTERED QUERY ROUTE
@router.get("/assets", response_model=InventoryResponse)
def get_assets_paginated(
    page: int = Query(1, ge=1),
    pageSize: Optional[int] = Query(None),
    page_size: Optional[int] = Query(None),
    sortBy: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sortDir: Optional[str] = Query(None),
    sort_dir: Optional[str] = Query(None),
    sortOrder: Optional[str] = Query(None),
    sort_order: Optional[str] = Query(None),
    search: str = Query(""),
    folder_id: Optional[str] = Query(None),
    folderId: Optional[str] = Query(None),
    subfolder_path: Optional[str] = Query(None),
    subfolderPath: Optional[str] = Query(None),
    path_prefix: Optional[str] = Query(None),
    pathPrefix: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    asset_service = AssetService(db)
    
    # Resolve aliases
    final_page_size = page_size or pageSize or 50
    final_sort_by = sort_by or sortBy or "created_at"
    final_sort_dir = sort_dir or sortDir or sort_order or sortOrder or "desc"
    final_folder_id = folder_id or folderId
    final_subfolder_path = subfolder_path or subfolderPath or path_prefix or pathPrefix

    db_sort_by = final_sort_by
    if final_sort_by == "size":
        db_sort_by = "size_bytes"

    return asset_service.get_inventory(
        page=page,
        page_size=final_page_size,
        sort_by=db_sort_by,
        sort_dir=final_sort_dir,
        search=search,
        tags=tags,
        folder_id=final_folder_id,
        subfolder_path=final_subfolder_path
    )

@router.get("/asset/{id}", response_model=AssetResponse)
def get_asset_new(id: str, db: Session = Depends(get_db)):
    asset_service = AssetService(db)
    asset = asset_service.get_asset_by_id(id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset

@router.delete("/asset/{id}")
def delete_asset_new(id: str, db: Session = Depends(get_db)):
    asset_service = AssetService(db)
    deleted = asset_service.delete_asset(id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"deleted": True}

@router.put("/asset/{id}", response_model=AssetResponse)
def update_asset(id: str, asset_update: AssetUpdate, db: Session = Depends(get_db)):
    asset_service = AssetService(db)
    updated = asset_service.update_asset(id, asset_update)
    if not updated:
        raise HTTPException(status_code=404, detail="Asset not found")
    return updated

@router.get("/asset/{id}/download")
@router.get("/assets/{id}/download")
@router.get("/asset/{id}/content")
@router.get("/assets/{id}/content")
def download_asset_file(id: str, db: Session = Depends(get_db)):
    asset_service = AssetService(db)
    asset = asset_service.get_asset_by_id(id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    abs_file_path = asset_service.get_asset_file_path(id)
    if not abs_file_path or not os.path.exists(abs_file_path):
        raise HTTPException(status_code=404, detail="Physical file not found on disk")
        
    return FileResponse(
        path=abs_file_path,
        filename=asset.original_name,
        media_type=asset.mime_type or "application/octet-stream",
        content_disposition_type="inline"
    )

@router.get("/assets/download-zip")
def download_multiple_assets(
    ids: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    import tempfile
    
    asset_ids = [i.strip() for i in ids.split(",") if i.strip()]
    if not asset_ids:
        raise HTTPException(status_code=400, detail="No asset IDs provided")
        
    asset_service = AssetService(db)
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    temp_zip_path = temp_zip.name
    temp_zip.close()
    
    try:
        asset_service.create_assets_zip(asset_ids, temp_zip_path)
    except Exception as e:
        if os.path.exists(temp_zip_path):
            os.unlink(temp_zip_path)
        raise HTTPException(status_code=500, detail=f"Failed to create download package: {str(e)}")
        
    background_tasks.add_task(remove_file, temp_zip_path)
    
    return FileResponse(
        path=temp_zip_path,
        filename="assetvault_downloads.zip",
        media_type="application/zip"
    )

@router.post("/assets/tags/add")
def batch_add_tags_endpoint(payload: BatchTagRequest, db: Session = Depends(get_db)):
    asset_service = AssetService(db)
    count = asset_service.batch_add_tags(payload.asset_ids, payload.tags)
    return {"updated_count": count, "message": f"Added tags to {count} asset(s)"}

@router.post("/assets/tags/remove")
def batch_remove_tags_endpoint(payload: BatchTagRequest, db: Session = Depends(get_db)):
    asset_service = AssetService(db)
    count = asset_service.batch_remove_tags(payload.asset_ids, payload.tags)
    return {"updated_count": count, "message": f"Removed tags from {count} asset(s)"}

@router.post("/assets/tags/replace")
def batch_replace_tag_endpoint(payload: BatchTagReplaceRequest, db: Session = Depends(get_db)):
    asset_service = AssetService(db)
    count = asset_service.batch_replace_tag(payload.asset_ids, payload.old_tag, payload.new_tag)
    return {"updated_count": count, "message": f"Replaced tag on {count} asset(s)"}

@router.post("/assets/tags/set")
def batch_set_tags_endpoint(payload: BatchTagRequest, db: Session = Depends(get_db)):
    asset_service = AssetService(db)
    count = asset_service.batch_set_tags(payload.asset_ids, payload.tags)
    return {"updated_count": count, "message": f"Set tags on {count} asset(s)"}


@router.post("/assets/scan-import")
def scan_and_import_assets_endpoint(db: Session = Depends(get_db)):
    asset_service = AssetService(db)
    try:
        return asset_service.scan_and_import_untracked_files()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan and import failed: {str(e)}")

class PurgeRequest(BaseModel):
    password: str

@router.post("/assets/purge")
def purge_assets(req_body: PurgeRequest, db: Session = Depends(get_db)):
    if req_body.password != settings.SYSTEM_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")
    asset_service = AssetService(db)
    count = asset_service.purge_all_assets()
    return {"message": "All assets successfully purged", "count": count}

def remove_file(path: str):
    import logging
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        logging.getLogger("assetvault").error("Failed to delete temp backup file: %s", e)

@router.get("/assets/backup")
def download_backup(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    asset_service = AssetService(db)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    storage_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "..", "storage"))
    os.makedirs(storage_dir, exist_ok=True)
    
    import uuid
    backup_filename = f"assetvault_backup_{uuid.uuid4().hex[:8]}.zip"
    temp_zip_path = os.path.join(storage_dir, backup_filename)
    
    try:
        asset_service.create_backup_zip(temp_zip_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create backup archive: {str(e)}")
        
    background_tasks.add_task(remove_file, temp_zip_path)
    
    return FileResponse(
        path=temp_zip_path,
        filename="assetvault_backup.zip",
        media_type="application/zip"
    )

@router.get("/assets/backup/csv")
def download_backup_csv(db: Session = Depends(get_db)):
    from fastapi import Response
    asset_service = AssetService(db)
    try:
        csv_content = asset_service.generate_assets_csv()
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=assetvault_db_backup.csv"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate CSV backup: {str(e)}")

@router.post("/assets/restore/csv")
async def restore_db_from_csv(file: UploadFile, db: Session = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
        
    asset_service = AssetService(db)
    try:
        contents = await file.read()
        csv_content = contents.decode("utf-8")
        count = asset_service.restore_assets_from_csv(csv_content)
        return {"message": "Database successfully restored from CSV", "imported_count": count}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restoration failed: {str(e)}")

@router.post("/assets/restore/zip")
async def restore_db_from_zip(file: UploadFile, db: Session = Depends(get_db)):
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files are supported")
        
    asset_service = AssetService(db)
    try:
        contents = await file.read()
        count = asset_service.restore_from_backup_zip(contents)
        return {"message": "Database and storage successfully restored from ZIP", "restored_count": count}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restoration failed: {str(e)}")

@router.get("/assets/verify")
def verify_assets_endpoint(db: Session = Depends(get_db)):
    from fastapi import Response
    asset_service = AssetService(db)
    try:
        log_content = asset_service.verify_assets_integrity()
        return Response(
            content=log_content,
            media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=assetvault_integrity_report.log"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")




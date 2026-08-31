from sqlalchemy.orm import Session
from app.models.asset import Asset
from app.models.tag import Tag
from typing import List, Optional

class AssetRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_all(self) -> List[Asset]:
        return self.db.query(Asset).all()

    def find_by_id(self, id: str) -> Optional[Asset]:
        return self.db.query(Asset).filter(Asset.id == id).first()

    def find_by_storage_path(self, storage_path: str) -> Optional[Asset]:
        return self.db.query(Asset).filter(Asset.storage_path == storage_path).first()

    def find_by_folder_id(self, folder_id: str) -> List[Asset]:
        return self.db.query(Asset).filter(Asset.folder_id == folder_id).all()

    def count_by_folder_id(self, folder_id: str) -> int:
        return self.db.query(Asset).filter(Asset.folder_id == folder_id).count()

    def create(self, asset_data: dict) -> Asset:
        tags = asset_data.pop("tags", [])
        asset = Asset(**asset_data)
        asset.tags = tags
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def save(self, asset: Asset) -> Asset:
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def delete(self, id: str) -> bool:
        asset = self.find_by_id(id)
        if asset:
            self.db.delete(asset)
            self.db.commit()
            return True
        return False

    def add_tag(self, asset: Asset, tag: Tag) -> None:
        if tag not in asset.tags:
            asset.tags.append(tag)
            self.db.commit()
            self.db.refresh(asset)

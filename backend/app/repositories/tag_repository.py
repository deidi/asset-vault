from sqlalchemy.orm import Session
from app.models.tag import Tag
from typing import List, Optional

class TagRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_all(self) -> List[Tag]:
        return self.db.query(Tag).all()

    def find_by_name(self, name: str) -> Optional[Tag]:
        return self.db.query(Tag).filter(Tag.name == name).first()

    def find_by_id(self, id: str) -> Optional[Tag]:
        return self.db.query(Tag).filter(Tag.id == id).first()

    def create(self, name: str) -> Tag:
        tag = Tag(name=name)
        self.db.add(tag)
        self.db.commit()
        self.db.refresh(tag)
        return tag

    def delete(self, id: str) -> bool:
        tag = self.find_by_id(id)
        if not tag:
            return False
        self.db.delete(tag)
        self.db.commit()
        return True

    def update(self, id: str, name: str) -> Optional[Tag]:
        tag = self.find_by_id(id)
        if not tag:
            return None
        tag.name = name.strip()
        self.db.commit()
        self.db.refresh(tag)
        return tag

    def delete_unused(self) -> int:
        unused_tags = self.db.query(Tag).filter(~Tag.assets.any()).all()
        count = len(unused_tags)
        for tag in unused_tags:
            self.db.delete(tag)
        self.db.commit()
        return count



from sqlalchemy.orm import Session
from app.repositories.tag_repository import TagRepository
from app.models.tag import Tag
from typing import List, Optional

class TagService:
    def __init__(self, db: Session):
        self.tag_repo = TagRepository(db)

    def get_or_create_tag(self, name: str) -> Tag:
        normalized_name = name.strip()
        tag = self.tag_repo.find_by_name(normalized_name)
        if not tag:
            tag = self.tag_repo.create(normalized_name)
        return tag

    def get_all_tags(self) -> List[Tag]:
        return self.tag_repo.find_all()

    def delete_tag(self, id: str) -> bool:
        return self.tag_repo.delete(id)

    def update_tag(self, id: str, name: str) -> Optional[Tag]:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Tag name cannot be empty")
            
        existing = self.tag_repo.find_by_name(normalized_name)
        if existing and existing.id != id:
            raise ValueError(f"Tag with name '{normalized_name}' already exists")
            
        return self.tag_repo.update(id, normalized_name)

    def delete_unused_tags(self) -> int:
        return self.tag_repo.delete_unused()


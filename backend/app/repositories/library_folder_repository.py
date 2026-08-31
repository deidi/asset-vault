from sqlalchemy.orm import Session
from app.models.library_folder import LibraryFolder
from typing import List, Optional

class LibraryFolderRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_all(self, active_only: bool = False) -> List[LibraryFolder]:
        query = self.db.query(LibraryFolder)
        if active_only:
            query = query.filter(LibraryFolder.is_active.is_(True))
        return query.order_by(LibraryFolder.created_at.desc()).all()

    def find_by_id(self, id: str) -> Optional[LibraryFolder]:
        return self.db.query(LibraryFolder).filter(LibraryFolder.id == id).first()

    def find_by_path(self, path: str) -> Optional[LibraryFolder]:
        return self.db.query(LibraryFolder).filter(LibraryFolder.path == path).first()

    def create(self, folder: LibraryFolder) -> LibraryFolder:
        self.db.add(folder)
        self.db.commit()
        self.db.refresh(folder)
        return folder

    def save(self, folder: LibraryFolder) -> LibraryFolder:
        self.db.add(folder)
        self.db.commit()
        self.db.refresh(folder)
        return folder

    def delete(self, id: str) -> bool:
        folder = self.find_by_id(id)
        if folder:
            self.db.delete(folder)
            self.db.commit()
            return True
        return False

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.db.session import Base

class LibraryFolder(Base):
    __tablename__ = "library_folders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    path = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    is_recursive = Column(Boolean, nullable=False, default=True)
    auto_tag_folder = Column(Boolean, nullable=False, default=True)
    custom_tags = Column(String, nullable=True)  # Comma-separated or JSON list of tag names
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    assets = relationship("Asset", back_populates="folder")

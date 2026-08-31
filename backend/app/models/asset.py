import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.association import AssetTag

class Asset(Base):
    __tablename__ = "files"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    original_name = Column(String, nullable=False)
    mime_type = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    storage_path = Column(String, nullable=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # In-place library & media management additions
    folder_id = Column(String(36), ForeignKey("library_folders.id", ondelete="SET NULL"), nullable=True)
    file_modified_at = Column(DateTime, nullable=True)
    file_hash = Column(String, nullable=True)
    thumbnail_path = Column(String, nullable=True)

    tags = relationship("Tag", secondary=AssetTag, back_populates="assets", lazy="selectin")
    folder = relationship("LibraryFolder", back_populates="assets", lazy="selectin")

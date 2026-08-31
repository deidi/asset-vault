from sqlalchemy import Table, Column, String, ForeignKey
from app.db.session import Base

AssetTag = Table(
    "file_tags",
    Base.metadata,
    Column("file_id", String(36), ForeignKey("files.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", String(36), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
)

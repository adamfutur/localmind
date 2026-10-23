from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from backend.db.database import Base


class FileMetadata(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, unique=True, index=True)
    filename = Column(String, index=True)
    extension = Column(String)
    size = Column(Integer)
    created_at = Column(DateTime)
    modified_at = Column(DateTime)
    last_indexed_at = Column(DateTime, default=datetime.utcnow)
    summary = Column(Text, nullable=True)
    tags = Column(String, nullable=True) # Comma separated tags

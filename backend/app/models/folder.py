from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class Folder(Base):
    __tablename__ = "folders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("folders.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    paper_count = Column(Integer, default=0)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    parent = relationship("Folder", remote_side=[id], backref="children")
    user = relationship("User")

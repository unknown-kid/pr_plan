from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    query = Column(String(500), nullable=False)
    result_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PopularSearch(Base):
    __tablename__ = "popular_searches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query = Column(String(500), nullable=False, unique=True)
    search_count = Column(Integer, default=0)
    last_searched_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

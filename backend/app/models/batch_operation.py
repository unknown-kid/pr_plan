from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class BatchOperation(Base):
    __tablename__ = "batch_operations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    operation_type = Column(String(50), nullable=False)
    status = Column(String(20), default="pending")
    total_items = Column(Integer)
    processed_items = Column(Integer, default=0)
    success_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    paper_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False)
    operation_params = Column(JSON)
    error_log = Column(ARRAY(Text))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

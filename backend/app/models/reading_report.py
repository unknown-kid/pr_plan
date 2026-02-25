from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, JSON, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class ReadingReport(Base):
    __tablename__ = "reading_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    template_id = Column(UUID(as_uuid=True), ForeignKey("report_templates.id"))
    title = Column(String(200))
    content = Column(Text, nullable=False)
    model_id = Column(UUID(as_uuid=True), ForeignKey("user_ai_models.id"))
    generation_time = Column(Float)
    version = Column(Integer, default=1)
    status = Column(String(20), default="generating")
    focus_directions = Column(Text)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    paper = relationship("Paper")
    user = relationship("User")
    template = relationship("ReportTemplate")

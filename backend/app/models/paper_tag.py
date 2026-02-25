from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class PaperTag(Base):
    __tablename__ = "paper_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id = Column(
        UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False
    )
    tag = Column(String(50), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("paper_id", "tag", name="_paper_tag_uc"),)

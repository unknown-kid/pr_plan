from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Integer,
    BigInteger,
    Date,
    Text,
    ForeignKey,
    Computed,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, TSVECTOR
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class Paper(Base):
    __tablename__ = "papers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    authors = Column(ARRAY(String))
    abstract = Column(Text)
    publication_date = Column(Date)
    journal = Column(String(255))
    volume = Column(String(50))
    issue = Column(String(50))
    pages = Column(String(100))
    doi = Column(String(100))
    arxiv_id = Column(String(50))
    pdf_url = Column(String(500))
    pdf_path = Column(String(500))
    cover_image_url = Column(String(500))
    upload_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    total_pages = Column(Integer)
    file_size = Column(BigInteger)
    source_type = Column(String(20))
    source_url = Column(String(500))
    status = Column(String(20), default="processing")
    is_public = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True))
    folder_id = Column(UUID(as_uuid=True), ForeignKey("folders.id"), nullable=True)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    indexed_at = Column(DateTime(timezone=True))

    # 全文搜索向量
    search_vector = Column(TSVECTOR)

    total_chunks = Column(Integer, default=0)

    processed_chunks = Column(Integer, default=0)

    # Embedding model used for vectorization
    embedding_model_id = Column(
        UUID(as_uuid=True), ForeignKey("public_ai_models.id"), nullable=True
    )
    embedding_model_name = Column(String(100), nullable=True)

    upload_user = relationship("User")

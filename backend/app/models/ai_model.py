from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Integer,
    ForeignKey,
    JSON,
    LargeBinary,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class PublicAIModel(Base):
    __tablename__ = "public_ai_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    model_type = Column(
        String(20), nullable=False
    )  # 'embedding', 'chat', 'translation'
    provider = Column(String(50), nullable=False)
    api_key = Column(String(255), nullable=False)
    api_url = Column(String(500))
    model_name = Column(String(100), nullable=False)
    config = Column(JSON)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UserAIModel(Base):
    __tablename__ = "user_ai_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    model_type = Column(String(20), nullable=False)
    provider = Column(String(50), nullable=False)
    api_key = Column(String(255))
    api_key_encrypted = Column(LargeBinary)
    api_url = Column(String(500))
    model_name = Column(String(100), nullable=False)
    is_default = Column(Boolean, default=False)
    config = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")

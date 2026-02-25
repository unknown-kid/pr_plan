from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"))
    title = Column(String(200))
    model_id = Column(UUID(as_uuid=True), ForeignKey("user_ai_models.id"))
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
    paper = relationship("Paper")
    messages = relationship(
        "ConversationMessage", back_populates="session", cascade="all, delete-orphan"
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True), ForeignKey("conversation_sessions.id"), nullable=False
    )
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ConversationSession", back_populates="messages")

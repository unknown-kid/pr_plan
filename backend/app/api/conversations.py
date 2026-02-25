from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db, SessionLocal
from app.api.deps import get_current_user
from app.models.user import User
from app.models.conversation import ConversationSession, ConversationMessage
from app.services.chat_service import chat_service
from uuid import UUID
from pydantic import BaseModel

router = APIRouter()


class ChatRequest(BaseModel):
    paper_id: Optional[UUID] = None
    model_id: Optional[UUID] = None
    query: str
    rag_scope: str = "single"  # "single" = this paper, "all" = all papers
    report_id: Optional[UUID] = None  # Include a reading report as additional context


@router.post("/{session_id}/chat")
async def chat(
    session_id: UUID,
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = (
        db.query(ConversationSession)
        .filter(
            ConversationSession.id == session_id,
            ConversationSession.user_id == current_user.id,
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    paper_id = request.paper_id or session.paper_id

    # 1. 保存用户消息
    user_msg = ConversationMessage(
        session_id=session_id, role="user", content=request.query
    )
    db.add(user_msg)

    # Update session title based on first user question (max 20 chars)
    if session.message_count == 0:
        title = request.query[:20] + ("..." if len(request.query) > 20 else "")
        session.title = title

    db.commit()

    # 2. 获取历史消息
    history = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.session_id == session_id)
        .order_by(ConversationMessage.created_at.asc())
        .all()
    )

    messages = [{"role": m.role, "content": m.content} for m in history]

    # 3. 流式返回回答
    async def response_generator():
        new_db = SessionLocal()
        try:
            full_response = ""
            async for chunk in chat_service.chat_stream(
                new_db,
                user_id=current_user.id,
                messages=messages,
                paper_id=paper_id,
                model_id=request.model_id,
                rag_scope=request.rag_scope,
                report_id=request.report_id,
            ):
                full_response += chunk
                yield chunk

            asst_msg = ConversationMessage(
                session_id=session_id, role="assistant", content=full_response
            )
            new_db.add(asst_msg)
            session_row = (
                new_db.query(ConversationSession)
                .filter(ConversationSession.id == session_id)
                .first()
            )
            if session_row:
                session_row.message_count += 2
            new_db.commit()
        except Exception as exc:
            print(f"Chat stream error: {exc}")
        finally:
            new_db.close()

    return StreamingResponse(response_generator(), media_type="text/plain")


@router.post("/")
def create_session(
    paper_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = ConversationSession(
        user_id=current_user.id, paper_id=paper_id, title="新对话"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/")
def list_sessions(
    paper_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ConversationSession).filter(
        ConversationSession.user_id == current_user.id
    )
    if paper_id:
        query = query.filter(ConversationSession.paper_id == paper_id)
    return query.order_by(ConversationSession.updated_at.desc()).all()


@router.get("/{session_id}/messages")
def get_messages(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = (
        db.query(ConversationSession)
        .filter(
            ConversationSession.id == session_id,
            ConversationSession.user_id == current_user.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.session_id == session_id)
        .order_by(ConversationMessage.created_at.asc())
        .all()
    )
    return {"session": session, "messages": messages}


@router.delete("/{session_id}")
def delete_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = (
        db.query(ConversationSession)
        .filter(
            ConversationSession.id == session_id,
            ConversationSession.user_id == current_user.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()
    return {"message": "Session deleted"}

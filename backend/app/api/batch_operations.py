from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services import batch_operation_service
from uuid import UUID
from pydantic import BaseModel

router = APIRouter()


class BatchOpCreate(BaseModel):
    operation_type: str
    paper_ids: List[UUID]
    params: Optional[dict] = None


@router.post("/")
def create_batch_op(
    op_in: BatchOpCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return batch_operation_service.create_batch_operation(
        db,
        user_id=current_user.id,
        operation_type=op_in.operation_type,
        paper_ids=op_in.paper_ids,
        params=op_in.params,
    )


@router.get("/")
def list_batch_ops(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return batch_operation_service.list_batch_operations(db, user_id=current_user.id)


@router.get("/{op_id}")
def get_batch_op(
    op_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    op = batch_operation_service.get_batch_operation(db, batch_op_id=op_id)
    if not op or op.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Operation not found")
    return op

from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.batch_operation import BatchOperation
from app.tasks.vectorization_tasks import batch_vectorize_task
from app.tasks.paper_tasks import batch_delete_papers_task
from uuid import UUID


def create_batch_operation(
    db: Session,
    user_id: UUID,
    operation_type: str,
    paper_ids: List[UUID],
    params: Dict[str, Any] = None,
) -> BatchOperation:
    batch_op = BatchOperation(
        user_id=user_id,
        operation_type=operation_type,
        paper_ids=paper_ids,
        total_items=len(paper_ids),
        operation_params=params,
        status="pending",
    )
    db.add(batch_op)
    db.commit()
    db.refresh(batch_op)

    # 派发任务
    paper_ids_str = [str(pid) for pid in paper_ids]
    if operation_type == "vectorize":
        batch_vectorize_task.delay(str(batch_op.id), paper_ids_str, params)
    elif operation_type == "delete":
        batch_delete_papers_task.delay(str(batch_op.id), paper_ids_str)

    return batch_op


def get_batch_operation(db: Session, batch_op_id: UUID) -> BatchOperation:
    return db.query(BatchOperation).filter(BatchOperation.id == batch_op_id).first()


def list_batch_operations(db: Session, user_id: UUID) -> List[BatchOperation]:
    return (
        db.query(BatchOperation)
        .filter(BatchOperation.user_id == user_id)
        .order_by(BatchOperation.created_at.desc())
        .all()
    )

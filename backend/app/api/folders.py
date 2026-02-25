from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.folder import Folder
from app.models.paper import Paper
from app.services.paper_service import update_folder_paper_count
from uuid import UUID
import uuid as uuid_lib

router = APIRouter()


class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[UUID] = None


class FolderUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[UUID] = None


class FolderOut(BaseModel):
    id: UUID
    name: str
    parent_id: Optional[UUID]
    paper_count: int
    is_deleted: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class BatchMoveRequest(BaseModel):
    item_ids: List[str]
    item_types: List[str]
    target_folder_id: Optional[UUID] = None


class BatchCopyRequest(BaseModel):
    item_ids: List[str]
    item_types: List[str]
    target_folder_id: Optional[UUID] = None


def get_recursive_paper_count(db: Session, folder_id: UUID) -> int:
    """递归计算文件夹及其所有子文件夹的论文总数"""
    direct_count = (
        db.query(Paper)
        .filter(Paper.folder_id == folder_id, Paper.is_deleted == False)
        .count()
    )

    child_folders = (
        db.query(Folder)
        .filter(Folder.parent_id == folder_id, Folder.is_deleted == False)
        .all()
    )

    for child in child_folders:
        direct_count += get_recursive_paper_count(db, child.id)

    return direct_count


@router.get("/", response_model=List[FolderOut])
def list_folders(
    parent_id: Optional[UUID] = None,
    include_deleted: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Folder).filter(Folder.user_id == current_user.id)

    if not include_deleted:
        query = query.filter(Folder.is_deleted == False)

    if parent_id is None:
        query = query.filter(Folder.parent_id == None)
    else:
        query = query.filter(Folder.parent_id == parent_id)

    folders = query.order_by(Folder.created_at.desc()).all()

    for folder in folders:
        folder.paper_count = get_recursive_paper_count(db, folder.id)

    return folders


@router.get("/all", response_model=List[FolderOut])
def list_all_folders(
    include_deleted: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Folder).filter(Folder.user_id == current_user.id)

    if not include_deleted:
        query = query.filter(Folder.is_deleted == False)

    folders = query.order_by(Folder.created_at.desc()).all()

    for folder in folders:
        folder.paper_count = get_recursive_paper_count(db, folder.id)

    return folders


@router.post("/", response_model=FolderOut)
def create_folder(
    folder_in: FolderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    folder = Folder(
        name=folder_in.name,
        parent_id=folder_in.parent_id,
        user_id=current_user.id,
        paper_count=0,
        is_deleted=False,
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


@router.put("/{folder_id}", response_model=FolderOut)
def update_folder(
    folder_id: UUID,
    folder_in: FolderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    folder = (
        db.query(Folder)
        .filter(Folder.id == folder_id, Folder.user_id == current_user.id)
        .first()
    )
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    if folder_in.name:
        folder.name = folder_in.name
    if folder_in.parent_id is not None:
        if folder_in.parent_id == folder_id:
            raise HTTPException(status_code=400, detail="Cannot set parent to self")
        folder.parent_id = folder_in.parent_id

    db.commit()
    db.refresh(folder)
    return folder


@router.delete("/{folder_id}")
def delete_folder(
    folder_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    folder = (
        db.query(Folder)
        .filter(Folder.id == folder_id, Folder.user_id == current_user.id)
        .first()
    )
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Soft delete folder and its papers
    folder.is_deleted = True
    folder.deleted_at = datetime.utcnow()

    # Also soft delete papers in this folder
    db.query(Paper).filter(Paper.folder_id == folder_id).update(
        {Paper.is_deleted: True, Paper.deleted_at: datetime.utcnow()}
    )

    db.commit()
    return {"message": "Folder moved to trash"}


@router.post("/{folder_id}/restore")
def restore_folder(
    folder_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    folder = (
        db.query(Folder)
        .filter(Folder.id == folder_id, Folder.user_id == current_user.id)
        .first()
    )
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    folder.is_deleted = False
    folder.deleted_at = None

    # Restore papers in this folder
    db.query(Paper).filter(Paper.folder_id == folder_id).update(
        {Paper.is_deleted: False, Paper.deleted_at: None}
    )

    db.commit()
    return {"message": "Folder restored"}


@router.delete("/{folder_id}/permanent")
def permanent_delete_folder(
    folder_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import os
    from app.models.conversation import ConversationSession, ConversationMessage

    folder = (
        db.query(Folder)
        .filter(Folder.id == folder_id, Folder.user_id == current_user.id)
        .first()
    )
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    def collect_all_items(fld):
        all_folders = [fld]
        all_papers = []

        child_folders = db.query(Folder).filter(Folder.parent_id == fld.id).all()
        for child in child_folders:
            child_folders_result, child_papers = collect_all_items(child)
            all_folders.extend(child_folders_result)
            all_papers.extend(child_papers)

        papers = db.query(Paper).filter(Paper.folder_id == fld.id).all()
        all_papers.extend(papers)

        return all_folders, all_papers

    all_folders, all_papers = collect_all_items(folder)

    for paper in all_papers:
        sessions = (
            db.query(ConversationSession)
            .filter(ConversationSession.paper_id == paper.id)
            .all()
        )
        for session in sessions:
            db.query(ConversationMessage).filter(
                ConversationMessage.session_id == session.id
            ).delete()
            db.delete(session)

        if paper.pdf_path:
            try:
                pdf_path = str(paper.pdf_path)
                if pdf_path and os.path.exists(pdf_path):
                    os.remove(pdf_path)
            except:
                pass

        db.delete(paper)

    db.flush()

    for fld in all_folders:
        db.delete(fld)

    db.commit()
    return {"message": "Folder permanently deleted"}


@router.post("/batch/move")
def batch_move_items(
    request: BatchMoveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    affected_folder_ids = set()

    for item_id, item_type in zip(request.item_ids, request.item_types):
        if item_type == "folder":
            folder = (
                db.query(Folder)
                .filter(Folder.id == UUID(item_id), Folder.user_id == current_user.id)
                .first()
            )
            if folder:
                if folder.parent_id:
                    affected_folder_ids.add(folder.parent_id)
                if request.target_folder_id:
                    affected_folder_ids.add(request.target_folder_id)
                folder.parent_id = request.target_folder_id
        elif item_type == "paper":
            paper = db.query(Paper).filter(Paper.id == UUID(item_id)).first()
            if paper:
                if paper.folder_id:
                    affected_folder_ids.add(paper.folder_id)
                if request.target_folder_id:
                    affected_folder_ids.add(request.target_folder_id)
                paper.folder_id = request.target_folder_id

    db.commit()

    for folder_id in affected_folder_ids:
        update_folder_paper_count(db, folder_id)

    return {"message": f"Moved {len(request.item_ids)} items"}


@router.post("/batch/copy")
def batch_copy_items(
    request: BatchCopyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    copied_count = 0

    def copy_folder_recursive(
        source_folder: Folder, target_parent_id: Optional[UUID]
    ) -> int:
        new_folder = Folder(
            id=uuid_lib.uuid4(),
            name=source_folder.name,
            parent_id=target_parent_id,
            user_id=current_user.id,
            paper_count=0,
            is_deleted=False,
        )
        db.add(new_folder)
        db.flush()

        count = 0
        papers = (
            db.query(Paper)
            .filter(Paper.folder_id == source_folder.id, Paper.is_deleted == False)
            .all()
        )

        for paper in papers:
            new_paper = Paper(
                id=uuid_lib.uuid4(),
                title=paper.title,
                authors=paper.authors,
                abstract=paper.abstract,
                pdf_path=paper.pdf_path,
                pdf_url=paper.pdf_url,
                upload_user_id=current_user.id,
                folder_id=new_folder.id,
                status=paper.status,
                total_pages=paper.total_pages,
                file_size=paper.file_size,
            )
            db.add(new_paper)
            count += 1

        new_folder.paper_count = count

        child_folders = (
            db.query(Folder)
            .filter(Folder.parent_id == source_folder.id, Folder.is_deleted == False)
            .all()
        )

        for child in child_folders:
            count += copy_folder_recursive(child, new_folder.id)

        return count

    for item_id, item_type in zip(request.item_ids, request.item_types):
        if item_type == "folder":
            folder = (
                db.query(Folder)
                .filter(Folder.id == UUID(item_id), Folder.user_id == current_user.id)
                .first()
            )
            if folder:
                copied_count += copy_folder_recursive(folder, request.target_folder_id)
        elif item_type == "paper":
            paper = db.query(Paper).filter(Paper.id == UUID(item_id)).first()
            if paper:
                new_paper = Paper(
                    id=uuid_lib.uuid4(),
                    title=paper.title,
                    authors=paper.authors,
                    abstract=paper.abstract,
                    pdf_path=paper.pdf_path,
                    pdf_url=paper.pdf_url,
                    upload_user_id=current_user.id,
                    folder_id=request.target_folder_id,
                    status=paper.status,
                    total_pages=paper.total_pages,
                    file_size=paper.file_size,
                )
                db.add(new_paper)
                copied_count += 1

    db.commit()

    if request.target_folder_id:
        update_folder_paper_count(db, request.target_folder_id)

    return {"message": f"Copied {copied_count} items"}


@router.post("/{folder_id}/papers/{paper_id}")
def add_paper_to_folder(
    folder_id: UUID,
    paper_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    if folder_id:
        folder = (
            db.query(Folder)
            .filter(Folder.id == folder_id, Folder.user_id == current_user.id)
            .first()
        )
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")

    paper.folder_id = folder_id
    db.commit()
    return {"message": "Paper added to folder"}


@router.post("/none/papers/{paper_id}")
def move_paper_to_root(
    paper_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    paper.folder_id = None
    db.commit()
    return {"message": "Paper moved to root"}

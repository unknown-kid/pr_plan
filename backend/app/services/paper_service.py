from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.paper import Paper
from app.models.paper_tag import PaperTag
from app.models.folder import Folder
from app.schemas.paper import PaperCreate, PaperUpdate


def update_folder_paper_count(db: Session, folder_id: Optional[UUID]) -> None:
    if folder_id is None:
        return
    count = (
        db.query(Paper)
        .filter(Paper.folder_id == folder_id, Paper.is_deleted == False)
        .count()
    )
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if folder:
        folder.paper_count = count
        db.commit()


def get_paper(
    db: Session, paper_id: UUID, include_deleted: bool = False
) -> Optional[Paper]:
    query = db.query(Paper).filter(Paper.id == paper_id)
    if not include_deleted:
        query = query.filter(Paper.is_deleted == False)
    return query.first()


def get_papers(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    is_public: Optional[bool] = None,
    include_deleted: bool = False,
    folder_id: Optional[UUID] = None,
    filter_null_folder: bool = False,
) -> List[Paper]:
    query = db.query(Paper)
    if not include_deleted:
        query = query.filter(Paper.is_deleted == False)
    if is_public is not None:
        query = query.filter(Paper.is_public == is_public)
    if filter_null_folder:
        query = query.filter(Paper.folder_id == None)
    elif folder_id is not None:
        query = query.filter(Paper.folder_id == folder_id)
    return query.order_by(Paper.created_at.desc()).offset(skip).limit(limit).all()


def create_paper(db: Session, paper_in: PaperCreate, upload_user_id: UUID) -> Paper:
    db_paper = Paper(
        **paper_in.model_dump(), upload_user_id=upload_user_id, status="processing"
    )
    db.add(db_paper)
    db.commit()
    db.refresh(db_paper)
    return db_paper


def update_paper(db: Session, db_paper: Paper, paper_in: PaperUpdate) -> Paper:
    old_folder_id = db_paper.folder_id
    update_data = paper_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_paper, field, value)
    db.commit()
    db.refresh(db_paper)

    if "folder_id" in update_data:
        update_folder_paper_count(db, old_folder_id)
        update_folder_paper_count(db, db_paper.folder_id)

    return db_paper


def soft_delete_paper(db: Session, db_paper: Paper):
    folder_id = db_paper.folder_id
    db_paper.is_deleted = True
    db_paper.deleted_at = datetime.utcnow()
    db.commit()
    update_folder_paper_count(db, folder_id)
    return db_paper


def restore_paper(db: Session, db_paper: Paper):
    db_paper.is_deleted = False
    db_paper.deleted_at = None
    folder_id = db_paper.folder_id
    db.commit()
    update_folder_paper_count(db, folder_id)
    return db_paper


def move_paper_to_folder(
    db: Session, db_paper: Paper, new_folder_id: Optional[UUID]
) -> Paper:
    old_folder_id = db_paper.folder_id
    db_paper.folder_id = new_folder_id
    db.commit()
    update_folder_paper_count(db, old_folder_id)
    update_folder_paper_count(db, new_folder_id)
    return db_paper


def add_tag(db: Session, paper_id: UUID, tag: str, user_id: UUID) -> PaperTag:
    db_tag = PaperTag(paper_id=paper_id, tag=tag, created_by=user_id)
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag


def remove_tag(db: Session, paper_id: UUID, tag: str):
    db_tag = (
        db.query(PaperTag)
        .filter(PaperTag.paper_id == paper_id, PaperTag.tag == tag)
        .first()
    )
    if db_tag:
        db.delete(db_tag)
        db.commit()
    return True


def get_paper_tags(db: Session, paper_id: UUID) -> List[str]:
    tags = db.query(PaperTag).filter(PaperTag.paper_id == paper_id).all()
    return [t.tag for t in tags]

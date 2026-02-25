from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.personalization import (
    Favorite,
    ReadingProgress,
    Note,
    NoteCreate,
    NoteUpdate,
)
from app.services import user_service
from uuid import UUID

router = APIRouter()


@router.get("/favorites", response_model=List[Favorite])
def get_favorites(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return user_service.get_favorites(db, user_id=current_user.id)


@router.post("/favorites/{paper_id}", response_model=Favorite)
def add_favorite(
    paper_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return user_service.add_favorite(db, user_id=current_user.id, paper_id=paper_id)


@router.delete("/favorites/{paper_id}")
def remove_favorite(
    paper_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_service.remove_favorite(db, user_id=current_user.id, paper_id=paper_id)
    return {"message": "Favorite removed"}


@router.get("/reading-progress/{paper_id}", response_model=Optional[ReadingProgress])
def get_reading_progress(
    paper_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return user_service.get_reading_progress(
        db, user_id=current_user.id, paper_id=paper_id
    )


@router.put("/reading-progress/{paper_id}", response_model=ReadingProgress)
def update_reading_progress(
    paper_id: UUID,
    current_page: int,
    progress_percentage: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return user_service.update_reading_progress(
        db,
        user_id=current_user.id,
        paper_id=paper_id,
        page=current_page,
        percentage=progress_percentage,
    )


@router.get("/notes", response_model=List[Note])
def get_notes(
    paper_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return user_service.get_user_notes(db, user_id=current_user.id, paper_id=paper_id)


@router.post("/notes", response_model=Note)
def create_note(
    note_in: NoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return user_service.create_note(db, user_id=current_user.id, note_in=note_in)

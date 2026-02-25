from sqlalchemy.orm import Session
from app.models.user import User
from app.models.user_favorite import UserFavorite
from app.models.user_reading_progress import UserReadingProgress
from app.models.user_note import UserNote
from app.schemas.user import UserCreate, UserUpdate
from app.schemas.personalization import (
    FavoriteCreate,
    ReadingProgressCreate,
    NoteCreate,
    NoteUpdate,
)
from app.core.security import get_password_hash, verify_password
from uuid import UUID
from typing import List, Optional


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def create_user(db: Session, user_in: UserCreate):
    db_user = User(
        email=user_in.email,
        username=user_in.username,
        password_hash=get_password_hash(user_in.password),
        avatar_url=user_in.avatar_url,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, username_or_email: str, password: str):
    # 先尝试用户名
    user = get_user_by_username(db, username_or_email)
    if not user:
        # 再尝试邮箱
        user = get_user_by_email(db, username_or_email)

    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_favorites(db: Session, user_id: UUID) -> List[UserFavorite]:
    return db.query(UserFavorite).filter(UserFavorite.user_id == user_id).all()


def add_favorite(db: Session, user_id: UUID, paper_id: UUID):
    db_fav = UserFavorite(user_id=user_id, paper_id=paper_id)
    db.add(db_fav)
    db.commit()
    db.refresh(db_fav)
    return db_fav


def remove_favorite(db: Session, user_id: UUID, paper_id: UUID):
    db_fav = (
        db.query(UserFavorite)
        .filter(UserFavorite.user_id == user_id, UserFavorite.paper_id == paper_id)
        .first()
    )
    if db_fav:
        db.delete(db_fav)
        db.commit()
    return True


def update_reading_progress(
    db: Session, user_id: UUID, paper_id: UUID, page: int, percentage: int
):
    db_progress = (
        db.query(UserReadingProgress)
        .filter(
            UserReadingProgress.user_id == user_id,
            UserReadingProgress.paper_id == paper_id,
        )
        .first()
    )
    if db_progress:
        db_progress.current_page = page
        db_progress.progress_percentage = percentage
    else:
        db_progress = UserReadingProgress(
            user_id=user_id,
            paper_id=paper_id,
            current_page=page,
            progress_percentage=percentage,
        )
        db.add(db_progress)
    db.commit()
    db.refresh(db_progress)
    return db_progress


def get_reading_progress(db: Session, user_id: UUID, paper_id: UUID):
    return (
        db.query(UserReadingProgress)
        .filter(
            UserReadingProgress.user_id == user_id,
            UserReadingProgress.paper_id == paper_id,
        )
        .first()
    )


def create_note(db: Session, user_id: UUID, note_in: NoteCreate):
    db_note = UserNote(user_id=user_id, **note_in.model_dump())
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note


def get_user_notes(db: Session, user_id: UUID, paper_id: Optional[UUID] = None):
    query = db.query(UserNote).filter(UserNote.user_id == user_id)
    if paper_id:
        query = query.filter(UserNote.paper_id == paper_id)
    return query.all()

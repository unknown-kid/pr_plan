from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class FavoriteBase(BaseModel):
    paper_id: UUID


class FavoriteCreate(FavoriteBase):
    pass


class Favorite(FavoriteBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReadingProgressBase(BaseModel):
    paper_id: UUID
    current_page: int = 1
    progress_percentage: int = 0


class ReadingProgressCreate(ReadingProgressBase):
    pass


class ReadingProgress(ReadingProgressBase):
    id: UUID
    user_id: UUID
    last_read_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NoteBase(BaseModel):
    paper_id: UUID
    page_number: Optional[int] = None
    note_text: str
    highlighted_text: Optional[str] = None


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    note_text: Optional[str] = None
    highlighted_text: Optional[str] = None
    page_number: Optional[int] = None


class Note(NoteBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

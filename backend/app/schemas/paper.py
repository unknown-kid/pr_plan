from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date


class PaperBase(BaseModel):
    title: str
    authors: Optional[List[str]] = None
    abstract: Optional[str] = None
    publication_date: Optional[date] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    is_public: bool = True


class PaperCreate(PaperBase):
    pdf_url: Optional[str] = None


class PaperUpdate(BaseModel):
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    abstract: Optional[str] = None
    publication_date: Optional[date] = None
    is_public: Optional[bool] = None
    status: Optional[str] = None


class Paper(PaperBase):
    id: UUID
    pdf_url: Optional[str] = None
    pdf_path: Optional[str] = None
    cover_image_url: Optional[str] = None
    upload_user_id: Optional[UUID] = None
    total_pages: Optional[int] = None
    file_size: Optional[int] = None
    status: str
    is_deleted: bool = False
    folder_id: Optional[UUID] = None
    view_count: int
    created_at: datetime
    updated_at: datetime
    total_chunks: Optional[int] = 0
    processed_chunks: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class TagBase(BaseModel):
    tag: str


class TagCreate(TagBase):
    pass


class Tag(TagBase):
    id: UUID
    paper_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime


class ReportTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    template_type: str
    prompt_template: str
    structure: dict
    is_public: bool = True


class ReportTemplateCreate(ReportTemplateBase):
    pass


class ReportTemplate(ReportTemplateBase):
    id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReadingReportBase(BaseModel):
    paper_id: UUID
    template_id: Optional[UUID] = None
    title: Optional[str] = None


class ReadingReportCreate(ReadingReportBase):
    model_id: Optional[UUID] = None
    focus_directions: Optional[str] = None


class ReadingReport(ReadingReportBase):
    id: UUID
    user_id: Optional[UUID] = None
    content: str
    model_id: Optional[UUID] = None
    generation_time: Optional[float] = None
    version: int
    status: str
    focus_directions: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

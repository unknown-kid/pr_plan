from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.report import ReadingReport, ReadingReportCreate, ReportTemplate
from app.services.report_generation_service import report_gen_service
from app.models.report_template import ReportTemplate as ReportTemplateModel
from app.models.reading_report import ReadingReport as ReadingReportModel
from uuid import UUID

router = APIRouter()


@router.post("/generate", response_model=ReadingReport)
async def generate_report(
    request: ReadingReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await report_gen_service.generate_report(
            db,
            paper_id=request.paper_id,
            user_id=current_user.id,
            template_id=request.template_id,
            model_id=request.model_id,
            focus_directions=request.focus_directions,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[ReadingReport])
def list_reports(
    paper_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ReadingReportModel).filter(
        ReadingReportModel.user_id == current_user.id
    )
    if paper_id:
        query = query.filter(ReadingReportModel.paper_id == paper_id)
    return query.order_by(ReadingReportModel.created_at.desc()).all()


@router.get("/{report_id}", response_model=ReadingReport)
def get_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = (
        db.query(ReadingReportModel)
        .filter(
            ReadingReportModel.id == report_id,
            ReadingReportModel.user_id == current_user.id,
        )
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    return report


@router.delete("/{report_id}")
def delete_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = (
        db.query(ReadingReportModel)
        .filter(
            ReadingReportModel.id == report_id,
            ReadingReportModel.user_id == current_user.id,
        )
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    db.delete(report)
    db.commit()
    return {"message": "报告已删除"}


@router.get("/templates", response_model=List[ReportTemplate])
def list_templates(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return (
        db.query(ReportTemplateModel)
        .filter(
            (ReportTemplateModel.is_public == True)
            | (ReportTemplateModel.created_by == current_user.id)
        )
        .all()
    )

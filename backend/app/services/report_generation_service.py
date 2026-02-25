"""
Report generation service using CrewAI agents.
Handles both sync (for API) and async (for Celery) generation.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.paper import Paper
from app.models.reading_report import ReadingReport
from app.services.model_resolver import model_resolver
from app.utils.pdf_parser import StreamingPDFParser
import time
import os
from uuid import UUID


class ReportGenerationService:
    async def generate_report(
        self,
        db: Session,
        paper_id: UUID,
        user_id: UUID,
        template_id: Optional[UUID] = None,
        model_id: Optional[UUID] = None,
        focus_directions: Optional[str] = None,
    ) -> ReadingReport:
        """Create a report record in 'generating' status and dispatch to Celery."""
        paper = db.query(Paper).filter(Paper.id == paper_id).first()
        if not paper:
            raise ValueError("论文不存在")

        pdf_path = str(paper.pdf_path) if paper.pdf_path else None
        if not pdf_path or not os.path.exists(pdf_path):
            raise ValueError(f"PDF 文件不存在: {pdf_path}")

        # Resolve chat model for generation
        model_config = await model_resolver.resolve_model(
            db, user_id, "chat", user_preferred_id=model_id
        )
        if not model_config:
            raise ValueError("未配置对话模型，请先前往模型配置页面添加。")

        def get_attr(attr, default=None):
            if isinstance(model_config, dict):
                return model_config.get(attr, default)
            return getattr(model_config, attr, default)

        # Determine version
        existing = (
            db.query(ReadingReport)
            .filter(
                ReadingReport.paper_id == paper_id, ReadingReport.user_id == user_id
            )
            .order_by(ReadingReport.version.desc())
            .first()
        )
        version = (existing.version + 1) if existing else 1

        # Create report record in "generating" status
        report = ReadingReport(
            paper_id=paper_id,
            user_id=user_id,
            title=f"阅读报告 - {paper.title}",
            content="",
            model_id=get_attr("id"),
            version=version,
            status="generating",
            focus_directions=focus_directions,
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        # Dispatch to Celery
        from app.tasks.report_tasks import generate_report_task

        generate_report_task.delay(
            report_id=str(report.id),
            paper_id=str(paper_id),
            paper_title=str(paper.title),
            pdf_path=pdf_path,
            api_config={
                "api_key": get_attr("api_key"),
                "api_url": get_attr("api_url", "https://api.openai.com/v1"),
                "model_name": get_attr("model_name"),
            },
            focus_directions=focus_directions,
        )

        return report


report_gen_service = ReportGenerationService()

"""
Celery task for asynchronous report generation using CrewAI.
"""

import time
from typing import Optional
from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.reading_report import ReadingReport
from uuid import UUID


@celery_app.task(name="generate_report", bind=True, max_retries=1)
def generate_report_task(
    self,
    report_id: str,
    paper_id: str,
    paper_title: str,
    pdf_path: str,
    api_config: dict,
    focus_directions: Optional[str] = None,
):
    """
    Celery task that runs CrewAI agents to generate a paper reading report.

    The agent follows a 3-phase process:
    1. Skim-read: Quickly read the paper with user's focus directions, produce an outline
    2. Outline: Structure the report based on the skim-read analysis
    3. Deep-read: Re-read the paper in detail guided by the outline, generate final report
    """
    db = SessionLocal()
    try:
        report = (
            db.query(ReadingReport).filter(ReadingReport.id == UUID(report_id)).first()
        )
        if not report:
            print(f"[ReportTask] Report {report_id} not found")
            return

        print(f"[ReportTask] Starting report generation for paper: {paper_title}")
        if focus_directions:
            print(f"[ReportTask] User focus directions: {focus_directions}")
        start_time = time.time()

        # 1. Extract text from PDF
        from app.utils.pdf_parser import StreamingPDFParser

        parser = StreamingPDFParser(pdf_path, chunk_size=2000)
        sections = list(parser.extract_text_by_page())

        if not sections:
            report.status = "failed"
            report.error_message = "PDF 无法解析或内容为空"
            db.commit()
            return

        print(f"[ReportTask] Extracted {len(sections)} pages from PDF")

        # 2. Run CrewAI agent with 3-phase process
        from app.agents.paper_report_agent import generate_paper_report

        content = generate_paper_report(
            sections=sections,
            api_config=api_config,
            paper_title=paper_title,
            focus_directions=focus_directions,
        )

        generation_time = time.time() - start_time
        print(f"[ReportTask] Report generated in {generation_time:.1f}s")

        # 3. Save result
        report.content = content
        report.status = "completed"
        report.generation_time = generation_time
        db.commit()

        print(f"[ReportTask] Report {report_id} saved successfully")

    except Exception as e:
        print(f"[ReportTask] Error generating report: {e}")
        import traceback

        traceback.print_exc()

        try:
            report = (
                db.query(ReadingReport)
                .filter(ReadingReport.id == UUID(report_id))
                .first()
            )
            if report:
                report.status = "failed"
                report.error_message = str(e)[:500]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()

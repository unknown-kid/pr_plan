from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.embedding_service import embedding_service
from app.services.paper_service import get_paper, soft_delete_paper
from app.services.model_resolver import model_resolver
from app.models.paper import Paper
from app.models.folder import Folder
from app.models.batch_operation import BatchOperation
from app.models.conversation import ConversationSession, ConversationMessage
from datetime import datetime, timedelta
import asyncio
from typing import Optional, Any, List
import os
from uuid import UUID


def get_config_value(config: Any, key: str, default: Any = None):
    if isinstance(config, dict):
        return config.get(key, default)
    return getattr(config, key, default)


@celery_app.task(name="process_paper_upload")
def process_paper_upload_task(
    paper_id: str, user_id: str, embedding_model_id: Optional[str] = None
):
    db = SessionLocal()
    paper = None
    try:
        paper = get_paper(db, paper_id=UUID(paper_id))
        if not paper:
            return

        # 获取嵌入模型配置
        embedding_config = asyncio.run(
            model_resolver.resolve_model(
                db,
                UUID(user_id),
                "embedding",
                user_preferred_id=UUID(embedding_model_id)
                if embedding_model_id
                else None,
            )
        )

        if not embedding_config:
            print(f"Error: No embedding model found for user {user_id}")
            paper.status = "error"
            db.commit()
            return

        # Prepare config dict
        config_dict = {
            "api_key": get_config_value(embedding_config, "api_key"),
            "api_url": get_config_value(embedding_config, "api_url"),
            "model_name": get_config_value(
                embedding_config, "model_name", "text-embedding-ada-002"
            ),
            "provider": get_config_value(embedding_config, "provider", "openai"),
        }

        # Set environment variables as a fallback
        if config_dict.get("provider") == "openai":
            if config_dict.get("api_key"):
                os.environ["OPENAI_API_KEY"] = config_dict["api_key"]
            if config_dict.get("api_url"):
                os.environ["OPENAI_API_BASE"] = config_dict["api_url"]

        asyncio.run(
            embedding_service.vectorize_paper(
                db,
                paper,
                config_dict,
            )
        )

        paper.status = "indexed"
        db.commit()
    except Exception as e:
        print(f"Exception in process_paper_upload_task: {str(e)}")
        if paper:
            # Re-fetch paper to avoid detached session issues if needed
            paper.status = "error"
            db.commit()
    finally:
        db.close()


@celery_app.task(name="batch_delete_papers")
def batch_delete_papers_task(batch_op_id: str, paper_ids: List[str]):
    db = SessionLocal()
    try:
        batch_op = (
            db.query(BatchOperation)
            .filter(BatchOperation.id == UUID(batch_op_id))
            .first()
        )
        if not batch_op:
            return

        batch_op.status = "processing"
        batch_op.started_at = datetime.utcnow()
        db.commit()

        for paper_id in paper_ids:
            try:
                paper = get_paper(db, paper_id=UUID(paper_id))
                if paper:
                    soft_delete_paper(db, paper)
                    batch_op.success_items += 1
                else:
                    batch_op.failed_items += 1
            except Exception as e:
                batch_op.failed_items += 1
                print(f"Error deleting paper {paper_id}: {str(e)}")

            batch_op.processed_items += 1
            db.commit()

        batch_op.status = "completed"
        batch_op.completed_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


@celery_app.task(name="cleanup_trash")
def cleanup_trash_task(days_old: int = 30):
    db = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        papers_to_delete = (
            db.query(Paper)
            .filter(Paper.is_deleted == True, Paper.deleted_at <= cutoff_date)
            .all()
        )

        papers_count = 0
        for paper in papers_to_delete:
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
                except Exception:
                    pass

            db.delete(paper)
            papers_count += 1

        folders_to_delete = (
            db.query(Folder)
            .filter(Folder.is_deleted == True, Folder.deleted_at <= cutoff_date)
            .all()
        )

        folders_count = 0
        for folder in folders_to_delete:
            db.delete(folder)
            folders_count += 1

        db.commit()
        print(
            f"Cleanup completed: deleted {papers_count} papers and {folders_count} folders"
        )
        return {"papers_deleted": papers_count, "folders_deleted": folders_count}
    except Exception as e:
        print(f"Error in cleanup_trash_task: {str(e)}")
        return {"error": str(e)}
    finally:
        db.close()

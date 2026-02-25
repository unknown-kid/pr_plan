from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.milvus_service import milvus_store
from app.services.embedding_client import EmbeddingClient
from app.services.model_resolver import model_resolver
from app.models.paper import Paper
from app.models.batch_operation import BatchOperation
from app.utils.pdf_parser import StreamingPDFParser
from datetime import datetime
import asyncio
from typing import Optional, Any
import os
from uuid import UUID


def get_config_value(config: Any, key: str, default: Any = None):
    if isinstance(config, dict):
        return config.get(key, default)
    return getattr(config, key, default)


@celery_app.task(name="batch_vectorize")
def batch_vectorize_task(
    batch_op_id: str, paper_ids: list, params: Optional[dict] = None
):
    db = SessionLocal()
    try:
        batch_op = (
            db.query(BatchOperation)
            .filter(BatchOperation.id == UUID(batch_op_id))
            .first()
        )
        if not batch_op:
            return

        user_id = batch_op.user_id
        embedding_model_id = params.get("embedding_model_id") if params else None

        batch_op.status = "processing"
        batch_op.started_at = datetime.utcnow()
        db.commit()

        embedding_config = asyncio.run(
            model_resolver.resolve_model(
                db,
                user_id,
                "embedding",
                user_preferred_id=UUID(embedding_model_id)
                if embedding_model_id
                else None,
            )
        )

        if not embedding_config:
            batch_op.status = "failed"
            batch_op.error_log = ["未配置嵌入模型，请先在模型配置中添加嵌入模型"]
            db.commit()
            return

        api_key = get_config_value(embedding_config, "api_key")
        api_url = get_config_value(
            embedding_config, "api_url", "https://api.openai.com/v1"
        )
        provider = get_config_value(embedding_config, "provider", "openai")
        model_name = get_config_value(
            embedding_config, "model_name", "text-embedding-ada-002"
        )
        model_id = get_config_value(embedding_config, "id")

        if not api_key:
            batch_op.status = "failed"
            batch_op.error_log = ["嵌入模型缺少 API Key"]
            db.commit()
            return

        if model_id and not isinstance(model_id, UUID):
            model_id = UUID(str(model_id))

        embedding_client = EmbeddingClient(
            api_key=api_key,
            api_url=api_url,
            model_name=model_name,
            provider=provider,
        )
        collection_name = milvus_store._get_collection_name(model_name)

        for paper_id in paper_ids:
            try:
                paper = db.query(Paper).filter(Paper.id == UUID(paper_id)).first()
                if not paper:
                    batch_op.failed_items += 1
                    batch_op.error_log = (batch_op.error_log or []) + [
                        f"Paper {paper_id} not found"
                    ]
                    batch_op.processed_items += 1
                    db.commit()
                    continue

                pdf_path = paper.pdf_path
                if not pdf_path:
                    batch_op.failed_items += 1
                    batch_op.error_log = (batch_op.error_log or []) + [
                        f"Paper {paper_id} has no PDF"
                    ]
                    batch_op.processed_items += 1
                    db.commit()
                    continue

                abs_path = pdf_path
                if not os.path.isabs(pdf_path):
                    abs_path = os.path.join("/app", pdf_path)
                if not os.path.exists(abs_path):
                    abs_path = os.path.join(os.getcwd(), pdf_path)

                if not os.path.exists(abs_path):
                    batch_op.failed_items += 1
                    batch_op.error_log = (batch_op.error_log or []) + [
                        f"PDF file not found: {pdf_path}"
                    ]
                    batch_op.processed_items += 1
                    db.commit()
                    continue

                parser = StreamingPDFParser(abs_path)
                chunks = list(parser.extract_chunks())

                paper.total_chunks = len(chunks)
                paper.processed_chunks = 0
                paper.embedding_model_id = model_id
                paper.embedding_model_name = model_name
                db.commit()

                batch_size = 10
                for i in range(0, len(chunks), batch_size):
                    batch_chunks = chunks[i : i + batch_size]
                    texts = [chunk["text"] for chunk in batch_chunks]
                    documents = [
                        {
                            "text": chunk["text"],
                            "metadata": {
                                "paper_id": str(paper.id),
                                "page": chunk.get("page", 0),
                                "chunk_index": chunk.get("chunk_index", i + j),
                            },
                        }
                        for j, chunk in enumerate(batch_chunks)
                    ]

                    embeddings = asyncio.run(embedding_client.get_embeddings(texts))

                    asyncio.run(
                        milvus_store.add_documents(
                            documents=documents,
                            embeddings=embeddings,
                            collection_name=collection_name,
                            paper_id=str(paper.id),
                        )
                    )

                    paper.processed_chunks += len(batch_chunks)
                    db.commit()

                paper.status = "indexed"
                batch_op.success_items += 1
                db.commit()

            except Exception as e:
                batch_op.failed_items += 1
                batch_op.error_log = (batch_op.error_log or []) + [
                    f"Error vectorizing {paper_id}: {str(e)}"
                ]

            batch_op.processed_items += 1
            db.commit()

        batch_op.status = "completed"
        batch_op.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        print(f"[Vectorization] Task error: {e}")
        if batch_op:
            batch_op.status = "failed"
            batch_op.error_log = (batch_op.error_log or []) + [str(e)]
            db.commit()
    finally:
        db.close()

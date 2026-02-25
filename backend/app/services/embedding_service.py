from typing import List, Dict, Any, Optional
from uuid import UUID
from app.core.knowledge_base.factory import KnowledgeBaseFactory
from app.utils.pdf_parser import StreamingPDFParser
from app.models.paper import Paper
from sqlalchemy.orm import Session
import os


class EmbeddingService:
    def __init__(self):
        self.vector_store = KnowledgeBaseFactory.create_vector_store()

    async def vectorize_paper(
        self,
        db: Session,
        paper: Paper,
        model_config: Dict[str, Any],
        embedding_model_id: Optional[UUID] = None,
        embedding_model_name: Optional[str] = None,
    ):
        if not paper.pdf_path or not os.path.exists(paper.pdf_path):
            raise FileNotFoundError(f"PDF file not found: {paper.pdf_path}")

        parser = StreamingPDFParser(paper.pdf_path)
        chunks = list(parser.extract_chunks())

        paper.total_chunks = len(chunks)
        paper.processed_chunks = 0
        # Save embedding model info to paper
        config_model_name = None
        if isinstance(model_config, dict):
            config_model_name = model_config.get("model_name")
        else:
            config_model_name = getattr(model_config, "model_name", None)

        if embedding_model_id:
            paper.embedding_model_id = embedding_model_id
        elif isinstance(model_config, dict) and model_config.get("id"):
            paper.embedding_model_id = model_config.get("id")

        if embedding_model_name:
            paper.embedding_model_name = embedding_model_name
        elif config_model_name:
            paper.embedding_model_name = config_model_name
        db.commit()

        # Process in batches to show progress
        batch_size = 5
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            documents = [
                {
                    "text": chunk["text"],
                    "metadata": {
                        "paper_id": str(paper.id),
                        "title": paper.title,
                        "page": chunk["page"],
                        "chunk_index": chunk["chunk_index"],
                    },
                }
                for chunk in batch
            ]

            await self.vector_store.add_documents(documents, model_config)

            paper.processed_chunks += len(batch)
            db.commit()

        paper.status = "indexed"
        db.commit()
        return True


embedding_service = EmbeddingService()

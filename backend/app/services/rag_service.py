from typing import List, Dict, Any, Optional
from app.services.milvus_service import milvus_store
from app.services.embedding_client import EmbeddingClient
from app.services.model_resolver import model_resolver
from app.models.paper import Paper
from sqlalchemy.orm import Session
from uuid import UUID
from pymilvus import utility


class RAGService:
    async def get_context(
        self,
        db: Session,
        user_id: UUID,
        query: str,
        paper_id: Optional[UUID] = None,
        top_k: int = 10,
        scope: str = "single",  # "single" = this paper only, "all" = all papers
    ) -> str:
        # Resolve embedding model
        embedding_config = await model_resolver.resolve_model(db, user_id, "embedding")
        if not embedding_config:
            print("[RAG] No embedding model configured")
            return ""

        api_key = getattr(embedding_config, "api_key", None)
        api_url = getattr(embedding_config, "api_url", "https://api.openai.com/v1")
        provider = getattr(embedding_config, "provider", "openai")
        model_name = getattr(embedding_config, "model_name", "text-embedding-ada-002")

        if not api_key:
            print("[RAG] No API key for embedding model")
            return ""

        # Generate query embedding
        try:
            embedding_client = EmbeddingClient(
                api_key=api_key,
                api_url=api_url,
                model_name=model_name,
                provider=provider,
            )
            query_embedding = await embedding_client.get_single_embedding(query)
            print(f"[RAG] Generated query embedding, length: {len(query_embedding)}")
        except Exception as e:
            print(f"[RAG] Failed to generate embedding: {e}")
            return ""

        if scope == "all":
            return await self._search_all_papers(db, query_embedding, top_k)
        else:
            return await self._search_single_paper(db, paper_id, query_embedding, top_k)

    async def _search_single_paper(
        self,
        db: Session,
        paper_id: Optional[UUID],
        query_embedding: List[float],
        top_k: int,
    ) -> str:
        if not paper_id:
            print("[RAG] No paper_id provided for single-paper search")
            return ""

        paper = db.query(Paper).filter(Paper.id == paper_id).first()
        if not paper:
            print(f"[RAG] Paper not found: {paper_id}")
            return ""

        embedding_model_name = getattr(paper, "embedding_model_name", None)
        if not embedding_model_name:
            print(f"[RAG] Paper not vectorized: {paper_id}")
            return ""

        collection_name = milvus_store._get_collection_name(embedding_model_name)

        try:
            results = await milvus_store.search(
                query_embedding=query_embedding,
                collection_name=collection_name,
                paper_id=str(paper_id),
                top_k=top_k,
            )
            print(
                f"[RAG] Single paper search - paper_id: {paper_id}, collection: {collection_name}, results: {len(results)}"
            )
        except Exception as e:
            print(f"[RAG] Milvus search error: {e}")
            return ""

        if results:
            context = "\n\n".join([r["text"] for r in results])
            print(f"[RAG] Context length: {len(context)} chars")
            return context
        return ""

    async def _search_all_papers(
        self,
        db: Session,
        query_embedding: List[float],
        top_k: int,
    ) -> str:
        all_results = []
        try:
            milvus_store._connect()
            collections = utility.list_collections()
            for col_name in collections:
                try:
                    results = await milvus_store.search(
                        query_embedding=query_embedding,
                        collection_name=col_name,
                        paper_id=None,  # no filter -> search all papers
                        top_k=top_k,
                    )
                    all_results.extend(results)
                except Exception as e:
                    print(f"[RAG] Search error in collection {col_name}: {e}")
                    continue
            print(
                f"[RAG] All-papers search - collections: {len(collections)}, total results: {len(all_results)}"
            )
        except Exception as e:
            print(f"[RAG] Milvus error: {e}")
            return ""

        if not all_results:
            return ""

        # Sort by score desc and take top_k
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        top_results = all_results[:top_k]

        context = "\n\n".join([r["text"] for r in top_results])
        print(f"[RAG] All-papers context length: {len(context)} chars")
        return context


rag_service = RAGService()

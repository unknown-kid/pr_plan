import os
from app.core.knowledge_base.base import VectorStoreAdapter
from app.core.knowledge_base.milvus_adapter import MilvusVectorStoreAdapter
from app.core.knowledge_base.simple_vector_store import SimpleVectorStore


class KnowledgeBaseFactory:
    @classmethod
    def create_vector_store(
        cls, adapter_type: str = "milvus", **kwargs
    ) -> VectorStoreAdapter:
        adapter = os.getenv("RAG_VECTOR_STORE", adapter_type).strip().lower()
        if adapter == "milvus":
            return MilvusVectorStoreAdapter(**kwargs)
        if adapter == "langchain":
            return MilvusVectorStoreAdapter(**kwargs)
        if adapter == "simple":
            return SimpleVectorStore(**kwargs)
        raise ValueError(f"Unsupported adapter type: {adapter}")

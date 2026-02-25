from typing import List, Dict, Any, Optional
from app.core.knowledge_base.base import VectorStoreAdapter
from app.services.milvus_service import milvus_store
from app.services.embedding_client import EmbeddingClient


class MilvusVectorStoreAdapter(VectorStoreAdapter):
    def __init__(self):
        self.store = milvus_store

    def _get_embedding_config_values(self, config: Any) -> Dict[str, Any]:
        if isinstance(config, dict):
            return {
                "api_key": config.get("api_key"),
                "api_url": config.get("api_url"),
                "model_name": config.get("model_name", "text-embedding-ada-002"),
                "provider": config.get("provider", "openai"),
            }
        return {
            "api_key": getattr(config, "api_key", None),
            "api_url": getattr(config, "api_url", None),
            "model_name": getattr(config, "model_name", "text-embedding-ada-002"),
            "provider": getattr(config, "provider", "openai"),
        }

    def _create_embedding_client(self, config: Any) -> EmbeddingClient:
        values = self._get_embedding_config_values(config)
        return EmbeddingClient(
            api_key=values["api_key"],
            api_url=values["api_url"],
            model_name=values["model_name"],
            provider=values["provider"],
        )

    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embedding_config: Any,
        collection_name: Optional[str] = None,
    ) -> List[str]:
        values = self._get_embedding_config_values(embedding_config)
        client = self._create_embedding_client(embedding_config)

        texts = [doc["text"] for doc in documents]
        embeddings = await client.get_embeddings(texts)

        col_name = collection_name or self._get_collection_name(values["model_name"])

        paper_id = "unknown"
        if documents and "metadata" in documents[0]:
            paper_id = documents[0]["metadata"].get("paper_id", "unknown")

        return await self.store.add_documents(
            documents=documents,
            embeddings=embeddings,
            collection_name=col_name,
            paper_id=paper_id,
        )

    async def search(
        self,
        query: str,
        embedding_config: Any,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        values = self._get_embedding_config_values(embedding_config)
        client = self._create_embedding_client(embedding_config)

        query_embedding = await client.get_single_embedding(query)
        col_name = collection_name or self._get_collection_name(values["model_name"])

        paper_id = None
        if filters and "paper_id" in filters:
            paper_id = filters["paper_id"]

        return await self.store.search(
            query_embedding=query_embedding,
            collection_name=col_name,
            paper_id=paper_id,
            top_k=top_k,
        )

    async def delete_documents(self, filters: Dict[str, Any]):
        if "paper_id" in filters and "collection_name" in filters:
            await self.store.delete_by_paper(
                collection_name=filters["collection_name"],
                paper_id=filters["paper_id"],
            )

    async def delete_collection(self, collection_name: str):
        await self.store.delete_collection(collection_name)

    async def list_collections(self) -> List[str]:
        from pymilvus import utility, connections

        try:
            self.store._connect()
            return utility.list_collections()
        except Exception:
            return []

    def get_collection_name(self, model_name: str) -> str:
        return self.store._get_collection_name(model_name)

    def _get_collection_name(self, model_name: str) -> str:
        return self.store._get_collection_name(model_name)

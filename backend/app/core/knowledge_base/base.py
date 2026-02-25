from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class VectorStoreAdapter(ABC):
    @abstractmethod
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embedding_config: Dict[str, Any],
        collection_name: Optional[str] = None,
    ) -> List[str]:
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        embedding_config: Dict[str, Any],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def delete_documents(self, filters: Dict[str, Any]):
        pass

    @abstractmethod
    async def delete_collection(self, collection_name: str):
        pass

    @abstractmethod
    async def list_collections(self) -> List[str]:
        pass

    @abstractmethod
    def get_collection_name(self, model_name: str) -> str:
        pass


class EmbeddingModelAdapter(ABC):
    @abstractmethod
    async def embed_text(
        self, texts: List[str], config: Dict[str, Any]
    ) -> List[List[float]]:
        pass

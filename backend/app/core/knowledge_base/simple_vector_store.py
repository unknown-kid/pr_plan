from typing import List, Dict, Any, Optional
import os
import json
import re
import numpy as np
from app.core.knowledge_base.base import VectorStoreAdapter
from app.services.embedding_client import EmbeddingClient


class SimpleVectorStore(VectorStoreAdapter):
    def __init__(self, persist_directory: str = "./vector_store"):
        self.persist_directory = persist_directory

    def _get_collection_name(self, model_name: str) -> str:
        safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", model_name)
        safe_name = re.sub(r"_+", "_", safe_name).strip("_")
        if len(safe_name) < 3:
            safe_name = f"emb_{safe_name}"
        if len(safe_name) > 63:
            safe_name = safe_name[:63]
        return safe_name

    def get_collection_name(self, model_name: str) -> str:
        return self._get_collection_name(model_name)

    def _get_paths(self, collection: str) -> Dict[str, str]:
        os.makedirs(self.persist_directory, exist_ok=True)
        return {
            "vectors": os.path.join(self.persist_directory, f"{collection}.npy"),
            "docs": os.path.join(self.persist_directory, f"{collection}.json"),
        }

    def _load_collection(self, collection: str) -> Dict[str, Any]:
        paths = self._get_paths(collection)
        if os.path.exists(paths["vectors"]):
            vectors = np.load(paths["vectors"])
        else:
            vectors = np.zeros((0, 0), dtype=np.float32)
        if os.path.exists(paths["docs"]):
            with open(paths["docs"], "r", encoding="utf-8") as f:
                docs = json.load(f)
        else:
            docs = []
        return {"vectors": vectors, "docs": docs}

    def _save_collection(
        self, collection: str, vectors: np.ndarray, docs: List[Dict[str, Any]]
    ):
        paths = self._get_paths(collection)
        np.save(paths["vectors"], vectors.astype(np.float32))
        with open(paths["docs"], "w", encoding="utf-8") as f:
            json.dump(docs, f, ensure_ascii=False)

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

    def _get_model_name(self, config: Any) -> str:
        if isinstance(config, dict):
            return config.get("model_name") or "text-embedding-ada-002"
        return getattr(config, "model_name", "text-embedding-ada-002")

    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embedding_config: Any,
        collection_name: Optional[str] = None,
    ) -> List[str]:
        client = self._create_embedding_client(embedding_config)
        model_name = self._get_model_name(embedding_config)
        collection = collection_name or self._get_collection_name(model_name)
        texts = [doc["text"] for doc in documents]
        vectors = np.array(await client.get_embeddings(texts), dtype=np.float32)

        collection_data = self._load_collection(collection)
        existing_vectors = collection_data["vectors"]
        existing_docs = collection_data["docs"]

        if existing_vectors.size == 0:
            combined_vectors = vectors
        else:
            if existing_vectors.shape[1] != vectors.shape[1]:
                raise ValueError("Embedding dimension mismatch for collection")
            combined_vectors = np.vstack([existing_vectors, vectors])

        combined_docs = existing_docs + [
            {"text": doc["text"], "metadata": doc.get("metadata", {})}
            for doc in documents
        ]

        self._save_collection(collection, combined_vectors, combined_docs)
        return []

    async def search(
        self,
        query: str,
        embedding_config: Any,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        client = self._create_embedding_client(embedding_config)
        model_name = self._get_model_name(embedding_config)
        collection = collection_name or self._get_collection_name(model_name)

        collection_data = self._load_collection(collection)
        vectors = collection_data["vectors"]
        docs = collection_data["docs"]
        if vectors.size == 0 or not docs:
            return []

        if filters:
            filtered_vectors = []
            filtered_docs = []
            for idx, doc in enumerate(docs):
                metadata = doc.get("metadata", {})
                matches = True
                for key, value in filters.items():
                    if metadata.get(key) != value:
                        matches = False
                        break
                if matches:
                    filtered_vectors.append(vectors[idx])
                    filtered_docs.append(doc)
            if not filtered_vectors:
                return []
            vectors = np.array(filtered_vectors, dtype=np.float32)
            docs = filtered_docs

        query_vec = np.array(await client.get_single_embedding(query), dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1) + 1e-10
        qnorm = np.linalg.norm(query_vec) + 1e-10
        scores = np.dot(vectors, query_vec) / (norms * qnorm)

        top_k = min(top_k, len(scores))
        idxs = np.argpartition(-scores, top_k - 1)[:top_k]
        idxs = idxs[np.argsort(-scores[idxs])]

        results = []
        for idx in idxs:
            doc = docs[int(idx)]
            results.append(
                {
                    "text": doc.get("text", ""),
                    "metadata": doc.get("metadata", {}),
                    "score": float(scores[int(idx)]),
                }
            )
        return results

    async def delete_documents(self, filters: Dict[str, Any]):
        return None

    async def delete_collection(self, collection_name: str):
        paths = self._get_paths(collection_name)
        if os.path.exists(paths["vectors"]):
            os.remove(paths["vectors"])
        if os.path.exists(paths["docs"]):
            os.remove(paths["docs"])

    async def list_collections(self) -> List[str]:
        if not os.path.exists(self.persist_directory):
            return []
        collections = []
        for name in os.listdir(self.persist_directory):
            if name.endswith(".npy"):
                collections.append(name[:-4])
        return collections

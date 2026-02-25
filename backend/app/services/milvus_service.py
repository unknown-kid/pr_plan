import os
import re
from typing import List, Dict, Any, Optional
from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility,
)
import numpy as np


class MilvusVectorStore:
    def __init__(self):
        self.host = os.getenv("MILVUS_HOST", "milvus")
        self.port = os.getenv("MILVUS_PORT", "19530")
        self._connected = False
        self._collections: Dict[str, Collection] = {}

    def _connect(self):
        if not self._connected:
            try:
                connections.connect(
                    alias="default",
                    host=self.host,
                    port=self.port,
                    timeout=10,
                )
                self._connected = True
            except Exception as e:
                print(f"[Milvus] Connection failed: {e}")
                raise

    def _get_collection_name(self, model_name: str) -> str:
        safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", model_name)
        safe_name = re.sub(r"_+", "_", safe_name).strip("_")
        if len(safe_name) < 3:
            safe_name = f"col_{safe_name}"
        if len(safe_name) > 63:
            safe_name = safe_name[:63]
        return safe_name

    def _get_embedding_dim(self, model_name: str) -> int:
        dims = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-v1": 1536,
            "text-embedding-v2": 1536,
            "text-embedding-v3": 1024,
            "embedding-001": 768,
        }
        for key in dims:
            if key in model_name.lower():
                return dims[key]
        return 1536

    def _get_or_create_collection(self, collection_name: str, dim: int) -> Collection:
        self._connect()

        if collection_name in self._collections:
            return self._collections[collection_name]

        if utility.has_collection(collection_name):
            collection = Collection(collection_name)
        else:
            fields = [
                FieldSchema(
                    name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100
                ),
                FieldSchema(name="paper_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="chunk_index", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="page", dtype=DataType.INT64),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
            ]
            schema = CollectionSchema(fields, description="Paper chunks collection")
            collection = Collection(collection_name, schema)

            index_params = {
                "metric_type": "COSINE",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 1024},
            }
            collection.create_index(field_name="embedding", index_params=index_params)
            print(f"[Milvus] Created collection: {collection_name}")

        self._collections[collection_name] = collection
        return collection

    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]],
        collection_name: str,
        paper_id: str,
    ) -> List[str]:
        if not documents or not embeddings:
            return []

        collection = self._get_or_create_collection(collection_name, len(embeddings[0]))

        ids = []
        data = []
        for i, (doc, emb) in enumerate(zip(documents, embeddings)):
            metadata = doc.get("metadata", {})
            chunk_idx = metadata.get("chunk_index", i)
            doc_id = f"{paper_id}_c{chunk_idx}"
            ids.append(doc_id)
            data.append(
                {
                    "id": doc_id,
                    "paper_id": str(metadata.get("paper_id", paper_id)),
                    "chunk_index": str(chunk_idx),
                    "page": int(metadata.get("page", 0)),
                    "text": doc.get("text", "")[:65000],
                    "embedding": emb,
                }
            )

        collection.insert(data)
        collection.flush()
        print(f"[Milvus] Inserted {len(data)} documents into {collection_name}")
        return ids

    async def search(
        self,
        query_embedding: List[float],
        collection_name: str,
        paper_id: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        self._connect()

        if not utility.has_collection(collection_name):
            print(f"[Milvus] Collection not found: {collection_name}")
            return []

        collection = Collection(collection_name)
        collection.load()

        search_params = {"metric_type": "COSINE", "params": {"nprobe": 16}}

        filter_expr = None
        if paper_id:
            filter_expr = f'paper_id == "{paper_id}"'

        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=filter_expr,
            output_fields=["text", "page", "chunk_index", "paper_id"],
        )

        output = []
        for hits in results:
            for hit in hits:
                try:
                    text = hit.entity.get("text")
                except Exception:
                    text = ""
                try:
                    page = hit.entity.get("page")
                except Exception:
                    page = None
                try:
                    chunk_index = hit.entity.get("chunk_index")
                except Exception:
                    chunk_index = None
                try:
                    paper_id_val = hit.entity.get("paper_id")
                except Exception:
                    paper_id_val = None

                output.append(
                    {
                        "text": text or "",
                        "score": 1 - hit.distance,
                        "metadata": {
                            "page": page,
                            "chunk_index": chunk_index,
                            "paper_id": paper_id_val,
                        },
                    }
                )
        return output

    async def delete_by_paper(self, collection_name: str, paper_id: str):
        self._connect()

        if not utility.has_collection(collection_name):
            return

        collection = Collection(collection_name)
        collection.delete(f'paper_id == "{paper_id}"')
        collection.flush()
        print(f"[Milvus] Deleted documents for paper: {paper_id}")

    async def delete_collection(self, collection_name: str):
        self._connect()

        if utility.has_collection(collection_name):
            utility.drop_collection(collection_name)
            print(f"[Milvus] Dropped collection: {collection_name}")

        if collection_name in self._collections:
            del self._collections[collection_name]


milvus_store = MilvusVectorStore()

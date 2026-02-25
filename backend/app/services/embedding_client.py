import httpx
import asyncio
from typing import List, Optional
import numpy as np


class EmbeddingClient:
    def __init__(
        self, api_key: str, api_url: str, model_name: str, provider: str = "openai"
    ):
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.model_name = model_name
        self.provider = provider

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if self.provider == "openai" or "openai" in self.provider.lower():
            return await self._get_openai_embeddings(texts)
        else:
            return await self._get_openai_embeddings(texts)

    async def _get_openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        url = f"{self.api_url}/embeddings"
        if "openai.com" in self.api_url:
            url = "https://api.openai.com/v1/embeddings"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        all_embeddings = []
        batch_size = 100

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            payload = {
                "model": self.model_name,
                "input": batch,
            }

            timeout = httpx.Timeout(60.0, connect=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code != 200:
                    raise Exception(
                        f"Embedding API error: {response.status_code} - {response.text}"
                    )

                data = response.json()
                embeddings = [item["embedding"] for item in data["data"]]
                all_embeddings.extend(embeddings)

        return all_embeddings

    async def get_single_embedding(self, text: str) -> List[float]:
        embeddings = await self.get_embeddings([text])
        return embeddings[0] if embeddings else []

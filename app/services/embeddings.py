from typing import List
import os
import openai


class EmbeddingService:
    """Embedding service using OpenAI embeddings API.

    Caches and persistence should be added (DB) for production.
    """

    def __init__(self, api_key: str | None = None, model: str = "text-embedding-3-small"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for embeddings")
        openai.api_key = self.api_key
        self.model = model

    def embed_text(self, text: str) -> List[float]:
        resp = openai.Embedding.create(model=self.model, input=text)
        return resp["data"][0]["embedding"]

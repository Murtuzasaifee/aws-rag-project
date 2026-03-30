"""
src/ragapp/services/embedding.py

Embedding service using AWS Bedrock Titan.
"""

from ragapp.core.config import get_settings


class EmbeddingService:
    def __init__(self):
        settings = get_settings()
        self._model_id = settings.embedding_model_id
        self._dimensions = settings.embedding_dimensions
        self._batch_size = settings.embedding_batch_size
        # TODO: Initialize Bedrock runtime client

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text using Bedrock Titan."""
        # TODO: Call Bedrock invoke_model with inputText
        raise NotImplementedError

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts."""
        # TODO: Process in batches of self._batch_size using embed_text
        raise NotImplementedError

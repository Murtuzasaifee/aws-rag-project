"""
src/ragapp/services/retrieval.py

RAG query pipeline: embed query -> search -> build context -> generate answer.
"""

import json
from typing import Any, Optional

from ragapp.services.embedding import EmbeddingService
from ragapp.storage.base import CacheStore, VectorStore


class RetrievalService:
    def __init__(
        self,
        vector_store: VectorStore,
        embedding_service: EmbeddingService,
        cache_store: Optional[CacheStore] = None,
    ):
        self._vector_store = vector_store
        self._embedding = embedding_service
        self._cache = cache_store

    async def query(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[dict[str, Any]] = None,
        min_score: float = 0.3,
    ) -> dict[str, Any]:
        """
        Full RAG query pipeline.

        Steps:
            1. Check cache for identical query
            2. Embed the query text
            3. Search vector store for similar chunks
            4. Filter results below min_score
            5. Build context from retrieved chunks
            6. Call Bedrock LLM with context + query
            7. Cache and return response

        Returns:
            dict with answer, sources, metadata
        """
        # TODO: Implement pipeline steps 1-7
        raise NotImplementedError

    async def _build_context(self, chunks: list[dict[str, Any]]) -> str:
        """Format retrieved chunks into a context string for the LLM prompt."""
        # TODO: Join chunk contents with source attribution
        raise NotImplementedError

    async def _generate_answer(self, query: str, context: str) -> str:
        """Call Bedrock LLM with the assembled prompt."""
        # TODO: Load prompt template, invoke Bedrock, return answer
        raise NotImplementedError

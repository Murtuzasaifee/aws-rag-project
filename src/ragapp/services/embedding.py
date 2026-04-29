"""
src/ragapp/services/embedding.py

Async embedding service using AWS Bedrock Runtime (Titan Text Embeddings v2 and compatible models).
"""

from __future__ import annotations

import asyncio
import json
import random
from typing import Any

from botocore.exceptions import ClientError

from ragapp.core.config import get_settings
from ragapp.logger import GLOBAL_LOGGER as logger

# Titan embedding APIs accept up to 25 input texts per logical batch for concurrent processing.
BEDROCK_EMBEDDING_MAX_BATCH = 25

# Retry Bedrock throttling and common transient faults with exponential backoff.
_RETRYABLE_ERROR_CODES = frozenset(
    {
        "ThrottlingException",
        "TooManyRequestsException",
        "ServiceUnavailable",
        "InternalServerException",
        "ModelTimeoutException",
        "ProvisionedThroughputExceededException",
    }
)

_MAX_RETRIES = 10
_RETRY_BASE_SECONDS = 0.5
_RETRY_MAX_SLEEP_SECONDS = 60.0


def _error_code(exc: ClientError) -> str:
    return exc.response.get("Error", {}).get("Code", "") or ""


def _should_retry(exc: BaseException) -> bool:
    if isinstance(exc, ClientError):
        return _error_code(exc) in _RETRYABLE_ERROR_CODES
    return False


class EmbeddingService:
    """Generate text embeddings via Bedrock ``invoke_model`` (async API, sync I/O in threads)."""

    def __init__(
        self,
        bedrock_client: Any | None = None,
        *,
        max_retries: int = _MAX_RETRIES,
        retry_base_seconds: float = _RETRY_BASE_SECONDS,
    ) -> None:
        settings = get_settings()
        self._model_id = settings.embedding_model_id
        self._dimensions = settings.embedding_dimensions
        self._batch_size = min(settings.embedding_batch_size, BEDROCK_EMBEDDING_MAX_BATCH)
        self._normalize = settings.embedding_normalize
        self._max_retries = max_retries
        self._retry_base_seconds = retry_base_seconds

        if bedrock_client is not None:
            self._client = bedrock_client
        else:
            from ragapp.core.dependencies import get_bedrock

            self._client = get_bedrock()

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def _invoke_sync(self, text: str) -> list[float]:
        body = json.dumps(
            {
                "inputText": text,
                "dimensions": self._dimensions,
                "normalize": self._normalize,
            }
        )
        response = self._client.invoke_model(
            modelId=self._model_id,
            body=body.encode("utf-8"),
            contentType="application/json",
            accept="application/json",
        )
        payload = json.loads(response["body"].read())
        embedding = payload.get("embedding")
        if not isinstance(embedding, list):
            raise RuntimeError("Bedrock response missing 'embedding' array")
        return [float(x) for x in embedding]

    async def _invoke_with_retry(self, text: str) -> list[float]:
        attempt = 0
        while True:
            try:
                return await asyncio.to_thread(self._invoke_sync, text)
            except ClientError as exc:
                if not _should_retry(exc) or attempt >= self._max_retries - 1:
                    logger.error(
                        "Bedrock embedding failed",
                        error_code=_error_code(exc),
                        attempt=attempt,
                        model_id=self._model_id,
                    )
                    raise
                delay = min(
                    self._retry_base_seconds * (2**attempt) + random.uniform(0, self._retry_base_seconds),
                    _RETRY_MAX_SLEEP_SECONDS,
                )
                logger.warning(
                    "Bedrock embedding transient error, retrying",
                    error_code=_error_code(exc),
                    attempt=attempt,
                    sleep_seconds=round(delay, 3),
                    model_id=self._model_id,
                )
                await asyncio.sleep(delay)
                attempt += 1

    async def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for a single string."""
        logger.debug("Embedding single text", preview=text[:50] if text else "")
        return await self._invoke_with_retry(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for many strings.

        Splits inputs into chunks of at most ``BEDROCK_EMBEDDING_MAX_BATCH`` (25) and processes
        each chunk concurrently. Order matches ``texts``.
        """
        if not texts:
            return []

        logger.debug("Embedding batch", count=len(texts), batch_size=self._batch_size)

        results: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            chunk = texts[start : start + self._batch_size]
            chunk_vectors = await asyncio.gather(*[self._invoke_with_retry(t) for t in chunk])
            results.extend(chunk_vectors)

        return results

    async def embed_query(self, text: str) -> list[float]:
        """Alias for :meth:`embed_text` (query / single-string use)."""
        return await self.embed_text(text)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Alias for :meth:`embed_batch` (document batch use)."""
        return await self.embed_batch(texts)


async def main():
    embedding_service = EmbeddingService()
    embedding = await embedding_service.embed_text("Hello, world!")
    print(embedding)

    batch = ["Hello, world!", "Hello, world!", "Hello, world!", "Hello, world!", "Hello, world!"]
    embeddings = await embedding_service.embed_batch(batch)
    print(embeddings)

    query = "Hello, world!"
    embedding = await embedding_service.embed_query(query)
    print(embedding)

if __name__ == "__main__":
    asyncio.run(main())
"""
src/ragapp/storage/base.py

Abstract base classes for all storage backends.
Swap implementations without changing business logic.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class DocumentStore(ABC):
    """Interface for raw document storage (e.g., S3, local filesystem)."""

    @abstractmethod
    async def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload a document. Returns the storage key."""

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Download a document by key."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a document by key."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a document exists."""

    @abstractmethod
    async def list_keys(self, prefix: str = "") -> list[str]:
        """List document keys under a prefix."""


class VectorStore(ABC):
    """Interface for vector storage and similarity search (e.g., OpenSearch, FAISS)."""

    @abstractmethod
    async def create_index(self, index_name: str, dimensions: int) -> None:
        """Create a vector index if it doesn't exist."""

    @abstractmethod
    async def index_chunks(self, index_name: str, chunks: list[dict[str, Any]]) -> int:
        """Index a batch of chunks with embeddings. Returns count indexed."""

    @abstractmethod
    async def search(
        self,
        index_name: str,
        query_vector: list[float],
        top_k: int = 5,
        filters: Optional[dict[str, Any]] = None,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Perform similarity search. Returns ranked results with scores."""

    @abstractmethod
    async def delete_by_document(self, index_name: str, document_id: str) -> int:
        """Delete all chunks for a document. Returns count deleted."""


class MetadataStore(ABC):
    """Interface for document metadata and status tracking (e.g., DynamoDB)."""

    @abstractmethod
    async def put(self, document_id: str, metadata: dict[str, Any]) -> None:
        """Store or update document metadata."""

    @abstractmethod
    async def get(self, document_id: str) -> Optional[dict[str, Any]]:
        """Retrieve document metadata. Returns None if not found."""

    @abstractmethod
    async def update_status(self, document_id: str, status: str, **extra_fields) -> None:
        """Update the processing status of a document."""

    @abstractmethod
    async def delete(self, document_id: str) -> None:
        """Delete document metadata."""

    @abstractmethod
    async def list_by_status(self, status: str) -> list[dict[str, Any]]:
        """List all documents with a given status."""


class CacheStore(ABC):
    """Interface for caching (e.g., Redis, in-memory)."""

    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """Get a cached value. Returns None on miss."""

    @abstractmethod
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """Set a cached value with optional TTL in seconds."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a cached value."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""

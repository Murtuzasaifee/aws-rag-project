"""
src/ragapp/services/ingest.py

Document ingestion pipeline: download -> chunk -> embed -> index.
"""

from typing import Any

from ragapp.services.embedding import EmbeddingService
from ragapp.storage.base import DocumentStore, MetadataStore, VectorStore


class IngestService:
    def __init__(
        self,
        document_store: DocumentStore,
        vector_store: VectorStore,
        metadata_store: MetadataStore,
        embedding_service: EmbeddingService,
    ):
        self._doc_store = document_store
        self._vector_store = vector_store
        self._metadata_store = metadata_store
        self._embedding = embedding_service

    async def ingest_document(
        self,
        s3_key: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Full ingestion pipeline for a document.

        Steps:
            1. Create tracking record in metadata store (status=pending)
            2. Download raw document from S3
            3. Extract text and chunk using chunking service
            4. Generate embeddings via Bedrock
            5. Index chunks + embeddings in vector store
            6. Update metadata status to completed

        Returns:
            dict with document_id, status, chunks_created, processing_time_seconds
        """
        # TODO: Implement pipeline steps 1-6
        raise NotImplementedError

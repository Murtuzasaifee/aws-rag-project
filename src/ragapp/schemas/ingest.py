"""
src/ragapp/schemas/ingest.py

Request and response schemas for:
  POST /ingest
  GET  /document/{id}/status
"""

from typing import Optional
from pydantic import BaseModel, Field


# ── Ingest Request ─────────────────────────────────────────────────────────────

class IngestMetadata(BaseModel):
    """Optional metadata attached to the document at ingestion time."""
    category: Optional[str] = None
    author: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class IngestRequest(BaseModel):
    """
    POST /ingest request body.

    Example:
        {
            "s3_key": "raw/my-document.pdf",
            "metadata": { "category": "technical", "author": "Jane Doe" }
        }
    """
    s3_key: str = Field(
        ...,
        description="S3 object key of the already-uploaded document (must be under raw/ prefix)"
    )
    metadata: IngestMetadata = Field(default_factory=IngestMetadata)


# ── Ingest Response ────────────────────────────────────────────────────────────

class IngestResponse(BaseModel):
    """
    POST /ingest response body.

    Example:
        {
            "job_id": "exec-abc123",
            "status": "processing",
            "document_id": "doc-uuid-here"
        }
    """
    job_id: str                             # Step Functions execution ARN (short form)
    status: str = "processing"
    document_id: str


# ── Status Response ────────────────────────────────────────────────────────────

class DocumentStatus(BaseModel):
    """
    GET /document/{id}/status response body.

    Possible status values:
      - processing        → Step Functions execution running
      - chunking_complete → document_processor done, waiting for embedding
      - completed         → fully indexed in OpenSearch
      - failed            → error at any pipeline step

    Example:
        {
            "document_id": "doc-uuid",
            "status": "completed",
            "chunks_created": 42,
            "processing_time_seconds": 18.4
        }
    """
    document_id: str
    status: str
    chunks_created: Optional[int] = None
    processing_time_seconds: Optional[float] = None
    error: Optional[str] = None             # populated on failure
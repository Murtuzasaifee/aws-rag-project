"""
src/ragapp/schemas/query.py

Request and response schemas for POST /query endpoint.
"""

from typing import Optional
from pydantic import BaseModel, Field


# ── Request ────────────────────────────────────────────────────────────────────


class QueryFilters(BaseModel):
    """Optional metadata filters applied during hybrid search."""

    category: Optional[str] = None
    document_id: Optional[str] = None
    page_number: Optional[int] = None


class QueryOptions(BaseModel):
    """Optional query behaviour overrides."""

    top_k: int = Field(
        default=5, ge=1, le=20, description="Number of chunks to retrieve"
    )
    stream: bool = Field(default=False, description="Streaming not yet implemented")


class QueryRequest(BaseModel):
    """
    POST /query request body.

    Example:
        {
            "query": "What is AWS Lambda?",
            "filters": { "category": "documentation" },
            "options": { "top_k": 5 }
        }
    """

    query: str = Field(..., min_length=1, max_length=2000, description="User question")
    filters: QueryFilters = Field(default_factory=QueryFilters)
    options: QueryOptions = Field(default_factory=QueryOptions)


# ── Response ───────────────────────────────────────────────────────────────────


class SourceChunk(BaseModel):
    """A single retrieved chunk returned as a source citation."""

    chunk_id: str
    content: str
    document_id: str
    score: float
    page_number: Optional[int] = None
    doc_item_type: Optional[str] = None


class QueryMetadata(BaseModel):
    """Metadata about how the query was processed."""

    cached: bool
    model: str
    chunks_retrieved: int
    latency_ms: Optional[int] = None


class QueryResponse(BaseModel):
    """
    POST /query response body.

    Example:
        {
            "answer": "AWS Lambda is a serverless compute service...",
            "sources": [ { "chunk_id": "...", "content": "...", ... } ],
            "metadata": { "cached": false, "model": "claude-3-5-sonnet", "chunks_retrieved": 5 }
        }
    """

    answer: str
    sources: list[SourceChunk]
    metadata: QueryMetadata

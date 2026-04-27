"""
Document upload and metadata schemas.

Pydantic models for document upload requests, responses, and metadata.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class DocumentStatus(str, Enum):
    """Document processing status."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    QUARANTINED = "quarantined"


class DocumentUploadResponse(BaseModel):
    """Response model for successful document upload."""

    document_id: UUID = Field(..., description="Unique document identifier")
    org_id: str = Field(..., description="Organization identifier")
    user_id: str = Field(..., description="User who uploaded the document")
    s3_key: str = Field(..., description="Full S3 object key")
    status: DocumentStatus = Field(default=DocumentStatus.UPLOADED)
    uploaded_at: datetime = Field(..., description="ISO 8601 timestamp")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "org_id": "acme",
                "user_id": "user_123",
                "s3_key": "raw/user_123/550e8400-e29b-41d4-a716-446655440000/report.pdf",
                "status": "uploaded",
                "uploaded_at": "2026-04-27T10:00:00Z",
            }
        }


class DocumentMetadata(BaseModel):
    """Full document metadata stored in DynamoDB."""

    # Keys
    org_id: str = Field(..., description="Partition key")
    document_id: UUID = Field(..., description="Sort key")

    # Ownership
    user_id: str = Field(..., description="Uploader's user ID")

    # File info
    original_filename: str = Field(..., description="Sanitised original filename")
    s3_bucket: str = Field(..., description="S3 bucket name")
    s3_key: str = Field(..., description="Full S3 object key")
    file_size_bytes: int = Field(..., ge=0)
    mime_type: str = Field(..., description="Detected MIME type")
    sha256_hash: str = Field(..., description="File hash for deduplication")

    # Status tracking
    status: DocumentStatus = Field(default=DocumentStatus.UPLOADED)
    uploaded_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    error_message: Optional[str] = Field(default=None)
    ttl: Optional[int] = Field(default=None, description="DynamoDB TTL for failed docs")

    # Metadata enrichment (added during processing)
    extracted_text: Optional[str] = Field(default=None)
    page_count: Optional[int] = Field(default=None)
    language: Optional[str] = Field(default=None)
    entities: Optional[list[dict]] = Field(default=None)

    class Config:
        """Pydantic config."""

        populate_by_name = True


class PresignedUrlRequest(BaseModel):
    """Request for pre-signed URL generation."""

    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., description="MIME type of the file")
    file_size: int = Field(..., gt=0, le=52428800, description="Size in bytes, max 50MB")

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Sanitise filename - remove path traversal and special chars."""
        # Remove path components
        v = v.replace("../", "").replace("..\\", "")
        # Get basename
        v = v.split("/")[-1].split("\\")[-1]
        # Remove special characters except alphanumeric, dash, underscore, dot
        v = re.sub(r"[^a-zA-Z0-9\-_\.]", "", v)
        # Remove leading dots (hidden files)
        v = v.lstrip(".")

        if not v:
            raise ValueError("Invalid filename after sanitization")

        return v

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        """Validate content type is allowed."""
        allowed_types = {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
            "image/png",
            "image/jpeg",
            "image/tiff",
            "application/msword",
        }
        if v not in allowed_types:
            raise ValueError(f"Content type '{v}' not allowed")
        return v


class PresignedUrlResponse(BaseModel):
    """Response containing pre-signed URL for direct S3 upload."""

    upload_url: str = Field(..., description="Pre-signed PUT URL")
    document_id: UUID = Field(..., description="Generated document UUID")
    expires_in: int = Field(..., description="URL expiry time in seconds")
    s3_key: str = Field(..., description="S3 key where file should be uploaded")


class DocumentListRequest(BaseModel):
    """Request for listing documents with filtering and pagination."""

    status: Optional[DocumentStatus] = Field(default=None)
    search: Optional[str] = Field(default=None, description="Search in filename")
    page_size: int = Field(default=20, ge=1, le=100)
    page_token: Optional[str] = Field(default=None)


class DocumentListResponse(BaseModel):
    """Response for document list."""

    documents: list[DocumentMetadata]
    next_page_token: Optional[str] = None
    total_count: int


class DocumentDeleteResponse(BaseModel):
    """Response for document deletion."""

    document_id: UUID
    deleted: bool
    message: str

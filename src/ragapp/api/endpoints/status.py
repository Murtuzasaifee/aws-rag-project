"""
src/ragapp/api/endpoints/status.py

GET /api/document/{document_id}/status — check ingestion status.
"""

from fastapi import APIRouter, Depends, HTTPException

from ragapp.schemas.ingest import DocumentStatus

router = APIRouter()


@router.get("/{document_id}/status", response_model=DocumentStatus)
async def get_document_status(document_id: str):
    """
    Retrieve the processing status of a document.

    TODO:
        - Get MetadataStore via dependency injection
        - Fetch document record from metadata_store.get(document_id)
        - Return 404 if not found
        - Map record to DocumentStatus schema
    """
    raise HTTPException(status_code=501, detail="Not implemented")

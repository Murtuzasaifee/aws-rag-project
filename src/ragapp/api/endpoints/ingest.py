"""
src/ragapp/api/endpoints/ingest.py

POST /api/ingest — trigger document ingestion pipeline.
"""

from fastapi import APIRouter, Depends, HTTPException

from ragapp.schemas.ingest import IngestRequest, IngestResponse

router = APIRouter()


@router.post("/", response_model=IngestResponse)
async def ingest_document(request: IngestRequest):
    """
    Accept an S3 key and kick off the ingestion pipeline.

    TODO:
        - Validate s3_key exists in bucket
        - Create IngestService with injected storage dependencies
        - Call ingest_service.ingest_document(request.s3_key, request.metadata)
        - Return IngestResponse with job_id, status, document_id
    """
    raise HTTPException(status_code=501, detail="Not implemented")

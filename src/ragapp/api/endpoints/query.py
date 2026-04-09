"""
src/ragapp/api/endpoints/query.py

POST /api/query — RAG query endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException

from ragapp.schemas.query import QueryRequest, QueryResponse

router = APIRouter()


@router.post("/", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """
    Accept a user query and return an LLM-generated answer with sources.

    TODO:
        - Create RetrievalService with injected dependencies
        - Call retrieval_service.query(request.query, request.options.top_k, ...)
        - Map results to QueryResponse schema
        - Return answer + sources + metadata
    """
    raise HTTPException(status_code=501, detail="Not implemented")

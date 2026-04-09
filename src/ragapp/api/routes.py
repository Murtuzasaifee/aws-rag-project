"""
src/ragapp/api/routes.py

Central router — imports and includes all endpoint sub-routers.
Add new endpoint modules here as the project grows.
"""

from fastapi import APIRouter

from ragapp.api.endpoints.query import router as query_router
from ragapp.api.endpoints.ingest import router as ingest_router
from ragapp.api.endpoints.status import router as status_router

router = APIRouter()

router.include_router(query_router, prefix="/query", tags=["Query"])
router.include_router(ingest_router, prefix="/ingest", tags=["Ingest"])
router.include_router(status_router, prefix="/document", tags=["Status"])

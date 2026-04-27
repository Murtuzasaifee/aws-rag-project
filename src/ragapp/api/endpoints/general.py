from fastapi import APIRouter
from ragapp.core.config import get_settings


router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    settings = get_settings()
    return {
        "status": "healthy",
        "version": settings.app_version,
        "service": settings.app_name
    }

@router.get("/")
async def root():
    """Root endpoint"""
    settings = get_settings()
    return {
        "message": f"Welcome to {settings.app_name}",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }
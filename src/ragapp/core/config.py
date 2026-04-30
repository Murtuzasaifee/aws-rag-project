"""
src/ragapp/core/config.py

Central configuration using Pydantic BaseSettings.
All values are read from environment variables or a .env file.
"""

from functools import lru_cache
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    For local development, create a .env file at the project root.
    In AWS Lambda, set these as Lambda environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────────────────────────
    app_name: str = "AWS Cloud Native RAG API"
    project_description: str = (
        "Production-ready AWS-native Retrieval-Augmented Generation (RAG) application."
    )
    app_version: str = "0.1.0"
    environment: str = "development"  # development | staging | production
    log_level: str = "INFO"
    # allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    allowed_origins: List[str] = ["*"]
    port: int | None = 8000

    # # ── AWS Region ─────────────────────────────────────────────────────────────
    # aws_region: str = "us-east-1"

    # # ── S3 ─────────────────────────────────────────────────────────────────────
    # s3_bucket_name: str  # e.g. rag-documents-dev
    # s3_raw_prefix: str = "raw/"
    # s3_processed_prefix: str = "processed/"
    # s3_failed_prefix: str = "failed/"
    # s3_chunks_prefix: str = "processed/chunks/"

    # # ── DynamoDB ───────────────────────────────────────────────────────────────
    # dynamodb_table_name: str = "documents"

    # # ── OpenSearch ─────────────────────────────────────────────────────────────
    # opensearch_endpoint: str  # e.g. https://xxx.us-east-1.es.amazonaws.com
    # opensearch_index: str = "rag-chunks"
    # opensearch_username: str = "admin"  # used for dev (anonymous access disabled)
    # opensearch_password: str = "admin"

    # # ── ElastiCache / Redis ────────────────────────────────────────────────────
    # redis_host: str  # e.g. rag-cache.xxx.cache.amazonaws.com
    # redis_port: int = 6379
    # redis_db: int = 0

    # # ── Bedrock — Embeddings ───────────────────────────────────────────────────
    bedrock_region: str = "us-east-1"
    embedding_model_id: str = "amazon.titan-embed-text-v2"
    embedding_dimensions: int = 1024
    embedding_batch_size: int = 25

    # # ── Bedrock — LLM ─────────────────────────────────────────────────────────
    llm_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.7

    # # ── Step Functions ─────────────────────────────────────────────────────────
    state_machine_arn: str = ""  # set after CDK deployment

    # # ── Retrieval ─────────────────────────────────────────────────────────────
    default_top_k: int = 5
    knn_candidates: int = 20  # kNN fetches 20, RRF narrows to top_k
    rrf_k_constant: int = 60  # standard RRF constant

    # # ── Cache TTLs (seconds) ──────────────────────────────────────────────────
    cache_ttl_embedding: int = 604800  # 7 days
    cache_ttl_query_result: int = 3600  # 1 hour
    cache_ttl_llm_response: int = 86400  # 24 hours

    # ── Document Processing ───────────────────────────────────────────────────
    max_file_size_mb: int = 50
    allowed_extensions: list[str] = [".pdf", ".txt", ".docx", ".png", ".jpeg", ".jpg"]
    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 50
    max_chunk_tokens: int = 512

    # ── System Prompt ─────────────────────────────────────────────────────────
    system_prompt: str = (
        "You are a helpful AI assistant. "
        "Answer questions based ONLY on the provided context. "
        "If the context does not contain the answer, say: "
        "'I don't have enough information to answer this question.' "
        "Always cite the source document when referencing information."
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    Use this everywhere instead of instantiating Settings() directly.

    Usage:
        from src.ragapp.core.config import get_settings
        settings = get_settings()
    """
    return Settings()

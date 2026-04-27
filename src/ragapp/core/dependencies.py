"""
src/ragapp/core/dependencies.py

Centralized AWS client and Redis client initialization.
All clients are created once and reused across the application.

Usage in FastAPI endpoints:
    from src.ragapp.core.dependencies import get_s3, get_bedrock, get_redis_client
"""

import boto3
import redis
from functools import lru_cache
from opensearchpy import OpenSearch, RequestsHttpConnection

from src.ragapp.core.config import get_settings

settings = get_settings()


# ── AWS Clients ────────────────────────────────────────────────────────────────


@lru_cache()
def get_s3():
    """S3 client for document storage."""
    return boto3.client("s3", region_name=settings.aws_region)


@lru_cache()
def get_dynamodb():
    """DynamoDB resource for document status tracking."""
    return boto3.resource("dynamodb", region_name=settings.aws_region)


@lru_cache()
def get_dynamodb_table():
    """DynamoDB table for document metadata."""
    dynamodb = get_dynamodb()
    return dynamodb.Table(settings.dynamodb_table_name)


@lru_cache()
def get_bedrock():
    """
    Bedrock runtime client for:
    - Embedding generation (Titan v2)
    - LLM inference (Claude 3.5 Sonnet)
    """
    return boto3.client(
        "bedrock-runtime",
        region_name=settings.bedrock_region,
    )


@lru_cache()
def get_stepfunctions():
    """Step Functions client for starting ingestion executions."""
    return boto3.client("stepfunctions", region_name=settings.aws_region)


# ── OpenSearch Client ──────────────────────────────────────────────────────────


@lru_cache()
def get_opensearch() -> OpenSearch:
    """
    OpenSearch client connected to the AWS OpenSearch Service domain.

    Dev mode: uses HTTP basic auth (admin/admin).
    The CDK stack sets the access policy to allow all for dev simplicity.
    """
    endpoint = settings.opensearch_endpoint.replace("https://", "").replace(
        "http://", ""
    )

    return OpenSearch(
        hosts=[{"host": endpoint, "port": 443}],
        http_auth=(settings.opensearch_username, settings.opensearch_password),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=30,
        max_retries=3,
        retry_on_timeout=True,
    )


# ── Redis Client ───────────────────────────────────────────────────────────────


@lru_cache()
def get_redis_client() -> redis.Redis:
    """
    Redis client for ElastiCache.

    Dev: no auth, no TLS (matches CacheStack config).
    Production: add ssl=True and password.
    """
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=True,  # return str instead of bytes
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
    )


# ── FastAPI Dependency Injectors ───────────────────────────────────────────────
# Use these in endpoint function signatures with Depends()


def s3_client():
    return get_s3()


def dynamodb_table():
    return get_dynamodb_table()


def bedrock_client():
    return get_bedrock()


def stepfunctions_client():
    return get_stepfunctions()


def opensearch_client():
    return get_opensearch()


def redis_client():
    return get_redis_client()

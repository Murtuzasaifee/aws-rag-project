"""
tests/conftest.py

Shared fixtures for unit and integration tests.
"""

import pytest


@pytest.fixture
def settings():
    """Override settings for test environment."""
    from ragapp.core.config import Settings

    return Settings(
        environment="test",
        s3_bucket_name="test-bucket",
        dynamodb_table_name="test-documents",
        opensearch_endpoint="https://localhost:9200",
        redis_host="localhost",
    )

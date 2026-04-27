"""
tests/unit/test_schemas.py

Unit tests for Pydantic request/response schemas.
"""

import pytest

from ragapp.schemas.ingest import IngestRequest, IngestResponse, DocumentStatus
from ragapp.schemas.query import QueryRequest, QueryResponse, QueryFilters, QueryOptions


class TestIngestSchemas:
    def test_ingest_request_valid(self):
        """IngestRequest should accept a valid s3_key."""
        # TODO: create IngestRequest with valid data, assert fields
        pass

    def test_ingest_request_requires_s3_key(self):
        """IngestRequest should reject missing s3_key."""
        # TODO: assert ValidationError when s3_key is missing
        pass

    def test_ingest_response_defaults(self):
        """IngestResponse.status should default to 'processing'."""
        # TODO: create IngestResponse, check status default
        pass

    def test_document_status_optional_fields(self):
        """DocumentStatus optional fields should default to None."""
        # TODO: verify chunks_created, processing_time_seconds, error are None
        pass


class TestQuerySchemas:
    def test_query_request_valid(self):
        """QueryRequest should accept a valid query string."""
        # TODO: create QueryRequest with valid data
        pass

    def test_query_request_min_length(self):
        """QueryRequest should reject empty query strings."""
        # TODO: assert ValidationError for empty query
        pass

    def test_query_options_defaults(self):
        """QueryOptions should have sensible defaults."""
        # TODO: verify top_k=5, stream=False
        pass

    def test_query_options_top_k_bounds(self):
        """QueryOptions.top_k should be between 1 and 20."""
        # TODO: assert ValidationError for top_k=0 and top_k=21
        pass

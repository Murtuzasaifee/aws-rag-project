"""
tests/integration/test_api.py

Integration tests for API endpoints using TestClient.
"""

import pytest
from fastapi.testclient import TestClient

from ragapp.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        """GET /health should return 200 with status=healthy."""
        # TODO: client.get("/health"), assert status_code == 200
        pass

    def test_health_response_shape(self, client):
        """Health response should contain status, version, service."""
        # TODO: verify response JSON has all required keys
        pass


class TestRootEndpoint:
    def test_root_returns_200(self, client):
        """GET / should return 200 with welcome message."""
        # TODO: client.get("/"), assert status_code == 200
        pass


class TestIngestEndpoint:
    def test_ingest_returns_501_not_implemented(self, client):
        """POST /api/ingest should return 501 until implemented."""
        # TODO: client.post("/api/ingest", json={...}), assert 501
        pass


class TestQueryEndpoint:
    def test_query_returns_501_not_implemented(self, client):
        """POST /api/query should return 501 until implemented."""
        # TODO: client.post("/api/query", json={...}), assert 501
        pass


class TestStatusEndpoint:
    def test_status_returns_501_not_implemented(self, client):
        """GET /api/document/{id}/status should return 501 until implemented."""
        # TODO: client.get("/api/document/doc-123/status"), assert 501
        pass

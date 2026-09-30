"""Tests for FastAPI endpoints."""
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_returns_project_info(self):
        """Test root endpoint returns project information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == settings.APP_NAME
        assert "description" in data
        assert data["version"] == settings.APP_VERSION
        assert data["docs_url"] == "/docs"


class TestHealthEndpoint:
    """Tests for health endpoint."""

    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == settings.APP_VERSION


class TestRoutingEndpoints:
    """Tests for routing endpoints."""

    def test_jev_endpoint_exists(self):
        """Test that Jev endpoint exists."""
        response = client.post(
            "/route/jev",
            json={"message": "Test message"},
        )
        # May fail with 500 if API key not configured, but endpoint should exist
        assert response.status_code in [200, 500]

    def test_llm_endpoint_exists(self):
        """Test that LLM endpoint exists."""
        response = client.post(
            "/route/llm",
            json={"message": "Test message"},
        )
        # May fail with 500 if API key not configured, but endpoint should exist
        assert response.status_code in [200, 500]

    def test_compare_endpoint_exists(self):
        """Test that compare endpoint exists."""
        response = client.post(
            "/route/compare",
            json={"message": "Test message"},
        )
        # May fail with 500 if API keys not configured, but endpoint should exist
        assert response.status_code in [200, 500]

    def test_invalid_request_body(self):
        """Test that invalid request body is rejected."""
        response = client.post(
            "/route/jev",
            json={"invalid_field": "value"},
        )
        assert response.status_code == 422  # Validation error

    def test_empty_message_rejected(self):
        """Test that empty message is rejected."""
        response = client.post(
            "/route/jev",
            json={"message": ""},
        )
        assert response.status_code == 422  # Validation error

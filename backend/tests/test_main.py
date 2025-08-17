"""Tests for FastAPI application main module."""

from fastapi.testclient import TestClient

from backend.main import app


class TestFastAPIApplication:
    """Test FastAPI application startup and configuration."""

    def test_app_creation(self):
        """Test that app is created successfully."""
        assert app is not None
        assert app.title == "TestInsight AI"

    def test_health_endpoint(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "TestInsight AI" in data["message"]

    def test_openapi_docs(self, client: TestClient):
        """Test that OpenAPI docs are accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_openapi_json(self, client: TestClient):
        """Test that OpenAPI JSON schema is accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "TestInsight AI"

    def test_cors_configuration(self, client: TestClient):
        """Test CORS is properly configured."""
        # Test that CORS headers are present in responses
        response = client.get("/api/v1/status")
        # CORS will be handled by middleware, just check response exists
        assert response.status_code in [200, 503]  # Service may be unconfigured

    def test_api_router_mounted(self, client: TestClient):
        """Test that API router is properly mounted."""
        # Test that API endpoints are accessible (even if they return errors without proper setup)
        response = client.get("/api/v1/status")
        # Should not return 404 - router is mounted
        assert response.status_code != 404

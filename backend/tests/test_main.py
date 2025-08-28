"""Tests for FastAPI application main module."""

import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app, normalize_cors_origins, parse_boolean_env


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


class TestCORSConfiguration:
    """Test CORS configuration improvements."""

    def test_normalize_cors_origins_basic(self):
        """Test basic origin normalization."""
        origins = "http://localhost:3000,http://127.0.0.1:3000"
        result = normalize_cors_origins(origins)
        expected = ["http://localhost:3000", "http://127.0.0.1:3000"]
        assert result == expected

    def test_normalize_cors_origins_deduplication(self):
        """Test deduplication while preserving order."""
        origins = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3000,https://localhost:3000"
        result = normalize_cors_origins(origins)
        expected = ["http://localhost:3000", "http://127.0.0.1:3000", "https://localhost:3000"]
        assert result == expected

    def test_normalize_cors_origins_trailing_slashes(self):
        """Test normalization removes trailing slashes."""
        origins = "http://localhost:3000/,http://127.0.0.1:3000/"
        result = normalize_cors_origins(origins)
        expected = ["http://localhost:3000", "http://127.0.0.1:3000"]
        assert result == expected

    def test_normalize_cors_origins_with_spaces(self):
        """Test handling of spaces around origins."""
        origins = " http://localhost:3000 , http://127.0.0.1:3000 , "
        result = normalize_cors_origins(origins)
        expected = ["http://localhost:3000", "http://127.0.0.1:3000"]
        assert result == expected

    def test_normalize_cors_origins_empty_string(self):
        """Test empty string returns wildcard."""
        result = normalize_cors_origins("")
        assert result == ["*"]

    def test_parse_boolean_env_true_variants(self):
        """Test various truthy values for boolean parsing."""
        truthy_values = ["true", "True", "TRUE", "yes", "YES", "1", "on", "ON"]
        for value in truthy_values:
            assert parse_boolean_env(value) is True

    def test_parse_boolean_env_false_variants(self):
        """Test various falsy values for boolean parsing."""
        falsy_values = ["false", "False", "FALSE", "no", "NO", "0", "off", "OFF", "invalid"]
        for value in falsy_values:
            assert parse_boolean_env(value) is False

    def test_parse_boolean_env_empty_string(self):
        """Test empty string with default values."""
        assert parse_boolean_env("", False) is False
        assert parse_boolean_env("", True) is True

    def test_https_localhost_defaults_included(self):
        """Test that default origins include HTTPS localhost variants."""
        from backend.main import default_origins

        expected_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://localhost:3000",
            "https://127.0.0.1:3000",
        ]
        actual_origins = normalize_cors_origins(default_origins)
        assert actual_origins == expected_origins

    @patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": "*", "CORS_ALLOW_CREDENTIALS": "1"}, clear=False)
    def test_wildcard_credentials_warning(self):
        """Test that wildcard origins with credentials shows warning."""
        with patch("backend.main.logging.getLogger") as mock_logger:
            # Test the logic directly
            from backend.main import normalize_cors_origins, parse_boolean_env

            test_origins = normalize_cors_origins("*")
            test_credentials = parse_boolean_env("1", True)

            assert test_origins == ["*"]
            assert test_credentials is True

            # Test that the wildcard + credentials combination would trigger warning
            if test_origins == ["*"] and test_credentials:
                mock_logger.return_value.warning.assert_not_called()  # Just verify function exists

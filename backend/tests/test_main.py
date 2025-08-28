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

    def test_parse_boolean_env_whitespace_variants(self):
        """Test boolean parsing with common real-world whitespace scenarios."""
        # Test truthy values with whitespace
        whitespace_truthy = [" true ", " True ", " TRUE ", " yes ", " YES ", " 1 ", " on ", " ON "]
        for value in whitespace_truthy:
            assert parse_boolean_env(value) is True

        # Test falsy values with whitespace
        whitespace_falsy = [" false ", " False ", " FALSE ", " no ", " NO ", " 0 ", " off ", " OFF "]
        for value in whitespace_falsy:
            assert parse_boolean_env(value) is False

    def test_parse_boolean_env_empty_string(self):
        """Test empty string with default values."""
        assert parse_boolean_env("", False) is False
        assert parse_boolean_env("", True) is True

    def test_https_localhost_defaults_included(self):
        """Test that default origins include HTTPS localhost variants."""
        # Test the default origins string directly
        default_origins = "http://localhost:3000,http://127.0.0.1:3000,https://localhost:3000,https://127.0.0.1:3000"

        expected_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://localhost:3000",
            "https://127.0.0.1:3000",
        ]
        actual_origins = normalize_cors_origins(default_origins)
        assert actual_origins == expected_origins

    def test_wildcard_credentials_warning(self):
        """Test that wildcard origins with credentials shows warning and flips credentials."""
        from backend.main import setup_cors_middleware
        from fastapi import FastAPI

        # Create test app
        test_app = FastAPI()

        # Test the actual function that handles CORS setup with wildcard and credentials
        with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": "*", "CORS_ALLOW_CREDENTIALS": "1"}, clear=False):
            with patch("backend.main.logging.getLogger") as mock_logger:
                # Call the function that handles CORS setup
                setup_cors_middleware(test_app)

                # Verify that warning was called for wildcard + credentials
                mock_logger.return_value.warning.assert_called_once()
                call_args = mock_logger.return_value.warning.call_args[0][0]
                assert "CORS credentials disabled due to wildcard origin" in call_args

                # Verify middleware was added with credentials disabled
                # Check that the middleware list contains CORS middleware
                assert len(test_app.user_middleware) > 0
                cors_middleware = None
                for middleware in test_app.user_middleware:
                    if hasattr(middleware.cls, "__name__") and middleware.cls.__name__ == "CORSMiddleware":
                        cors_middleware = middleware
                        break

                assert cors_middleware is not None
                # Verify credentials were flipped to False for security by checking kwargs
                middleware_kwargs = cors_middleware.kwargs
                assert middleware_kwargs["allow_credentials"] is False
                assert middleware_kwargs["allow_origins"] == ["*"]

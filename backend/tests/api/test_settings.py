"""Tests for settings endpoints."""

from datetime import datetime
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from backend.models.schemas import AppSettings, JenkinsSettings, GitHubSettings, AISettings


def test_get_settings_error(client: TestClient):
    """Test error handling for get_settings."""
    with patch("backend.api.routers.settings.SettingsService") as mock_settings_service:
        mock_settings_service.side_effect = Exception("Test error")
        response = client.get("/api/v1/settings")
        assert response.status_code == 500


def test_update_settings_error(client: TestClient):
    """Test error handling for update_settings."""
    with patch("backend.api.routers.settings.SettingsService") as mock_settings_service:
        mock_settings_service.return_value.update_settings.side_effect = Exception("Test error")
        response = client.put("/api/v1/settings", json={})
        assert response.status_code == 500


def test_reset_settings_error(client: TestClient):
    """Test error handling for reset_settings."""
    with patch("backend.api.routers.settings.SettingsService") as mock_settings_service:
        mock_settings_service.return_value.reset_settings.side_effect = Exception("Test error")
        response = client.post("/api/v1/settings/reset")
        assert response.status_code == 500


def test_validate_settings_error(client: TestClient):
    """Test error handling for validate_settings."""
    with patch("backend.api.routers.settings.SettingsService") as mock_settings_service:
        mock_settings_service.return_value.validate_settings.side_effect = Exception("Test error")
        response = client.get("/api/v1/settings/validate")
        assert response.status_code == 500


def test_get_secrets_status(client: TestClient):
    """Test get_secrets_status endpoint."""
    with patch("backend.api.routers.settings.SettingsService") as mock_settings_service:
        mock_service_instance = Mock()
        mock_service_instance.get_secret_status.return_value = {
            "jenkins": {"api_token": True},
            "github": {"token": False},
            "ai": {"gemini_api_key": True},
        }
        mock_settings_service.return_value = mock_service_instance

        response = client.get("/api/v1/settings/secrets-status")

        assert response.status_code == 200
        data = response.json()
        assert data["jenkins"]["api_token"] is True
        assert data["github"]["token"] is False
        assert data["ai"]["gemini_api_key"] is True


def test_backup_settings(client: TestClient):
    """Test backup_settings endpoint."""
    with patch("backend.api.routers.settings.SettingsService") as mock_settings_service:
        mock_service_instance = Mock()
        mock_settings = Mock()
        mock_settings.model_dump.return_value = {"test": "data"}
        mock_service_instance.get_settings.return_value = mock_settings
        mock_settings_service.return_value = mock_service_instance

        response = client.get("/api/v1/settings/backup")

        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]


def test_restore_settings(client: TestClient):
    """Test restore_settings endpoint."""
    with patch("backend.api.routers.settings.SettingsService") as mock_settings_service:
        mock_service_instance = Mock()
        mock_settings = AppSettings(
            jenkins=JenkinsSettings(url="http://test.com"),
            github=GitHubSettings(token="test_token"),
            ai=AISettings(gemini_api_key="test_key"),
            last_updated=datetime.now(),
        )
        mock_service_instance.get_masked_settings.return_value = mock_settings
        mock_settings_service.return_value = mock_service_instance

        files = {
            "backup_file": (
                "test.txt",
                '{"jenkins": {"url": "http://test.com"}, "github": {"token": "test_token"}, "ai": {"gemini_api_key": "test_key"}}',
                "application/json",
            )
        }
        response = client.post("/api/v1/settings/restore", files=files)

        assert response.status_code == 200


def test_test_service_connection_jenkins_failure(client: TestClient):
    """Test test_service_connection with Jenkins failure."""
    with patch("backend.api.routers.settings.ServiceConnectionTesters") as mock_service_config:
        mock_service_config.return_value.test_jenkins_connection.side_effect = ConnectionError("Test error")
        response = client.post("/api/v1/settings/test-connection?service=jenkins")
        assert response.status_code == 200
        assert response.json()["success"] is False


def test_test_service_connection_github_failure(client: TestClient):
    """Test test_service_connection with GitHub failure."""
    with patch("backend.api.routers.settings.ServiceConnectionTesters") as mock_service_config:
        mock_service_config.return_value.test_github_connection.side_effect = ConnectionError("Test error")
        response = client.post("/api/v1/settings/test-connection?service=github")
        assert response.status_code == 200
        assert response.json()["success"] is False


def test_test_service_connection_ai_failure(client: TestClient):
    """Test test_service_connection with AI failure."""
    with patch("backend.api.routers.settings.ServiceConnectionTesters") as mock_service_config:
        mock_service_config.return_value.test_ai_connection.side_effect = ConnectionError("Test error")
        response = client.post("/api/v1/settings/test-connection?service=ai")
        assert response.status_code == 200
        assert response.json()["success"] is False


def test_test_service_connection_unknown_service(client: TestClient):
    """Test test_service_connection with an unknown service."""
    response = client.post("/api/v1/settings/test-connection?service=unknown")
    assert response.status_code == 400


def test_test_service_connection_with_config_unknown_service(client: TestClient):
    """Test test_service_connection_with_config with an unknown service."""
    response = client.post(
        "/api/v1/settings/test-connection-with-config",
        json={"service": "unknown", "config": {}},
    )
    assert response.status_code == 400

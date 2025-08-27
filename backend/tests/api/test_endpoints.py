"""Comprehensive tests for all API endpoints in the FastAPI application."""

import json
from datetime import datetime
from io import BytesIO
from unittest.mock import Mock, patch

import pytest

from backend.models.schemas import (
    AISettings,
    AppSettings,
    GeminiModelInfo,
    GeminiModelsResponse,
    GitHubSettings,
    JenkinsSettings,
)
from backend.api.routers.constants import (
    FAILED_VALIDATE_AUTHENTICATION,
    INVALID_API_KEY_FORMAT,
    INTERNAL_SERVER_ERROR_FETCHING_MODELS,
)
from backend.tests.conftest import (
    FAKE_GEMINI_API_KEY,
    FAKE_GITHUB_TOKEN,
    FAKE_INVALID_API_KEY,
    FAKE_INVALID_FORMAT_KEY,
    FAKE_JENKINS_TOKEN,
    FAKE_JENKINS_URL,
    FAKE_JENKINS_USERNAME,
)


class TestAnalyzeEndpoint:
    """Test the /api/v1/analyze endpoint."""

    @patch("backend.api.routers.analysis.ServiceClientCreators")
    def test_analyze_success(self, mock_service_config, client):
        """Test successful analysis."""
        # Mock AI analyzer
        mock_ai_analyzer = Mock()
        mock_analysis = Mock()
        mock_analysis.insights = []  # Keep it simple for now
        mock_analysis.summary = "Test analysis summary"
        mock_analysis.recommendations = ["Improve test coverage"]

        mock_ai_analyzer.analyze_test_results.return_value = mock_analysis
        mock_service_config.return_value.create_configured_ai_client.return_value = mock_ai_analyzer

        response = client.post(
            "/api/v1/analyze",
            data={"text": "fake test results", "custom_context": "fake context"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "insights" in data
        assert "summary" in data
        assert "recommendations" in data
        assert data["summary"] == "Test analysis summary"
        assert data["recommendations"] == ["Improve test coverage"]

    @patch("backend.api.routers.analysis.ServiceClientCreators")
    def test_analyze_no_ai_client(self, mock_service_config, client):
        """Test analysis when AI client is not configured."""
        mock_service_config.return_value.create_configured_ai_client.return_value = None

        response = client.post("/api/v1/analyze", data={"text": "fake test results"})

        assert response.status_code == 503
        assert "AI analyzer not configured" in response.json()["detail"]

    @patch("backend.api.routers.analysis.ServiceClientCreators")
    def test_analyze_missing_text(self, mock_service_config, client):
        """Test analysis with missing required text parameter."""
        response = client.post("/api/v1/analyze", data={})

        assert response.status_code == 422  # Validation error

    @patch("backend.api.routers.analysis.ServiceClientCreators")
    def test_analyze_service_error(self, mock_service_config, client):
        """Test analysis when service throws exception."""
        mock_ai_analyzer = Mock()
        mock_ai_analyzer.analyze_test_results.side_effect = Exception("Service error")
        mock_service_config.return_value.create_configured_ai_client.return_value = mock_ai_analyzer

        response = client.post("/api/v1/analyze", data={"text": "fake test results"})

        assert response.status_code == 500
        assert "Text analysis failed" in response.json()["detail"]


class TestJenkinsEndpoints:
    """Test Jenkins-related endpoints."""

    @patch("backend.api.routers.jenkins.ServiceClientCreators")
    def test_get_jenkins_jobs_success(self, mock_service_config, client):
        """Test successful retrieval of Jenkins jobs."""
        mock_jenkins_client = Mock()
        mock_jenkins_client.is_connected.return_value = True
        mock_jenkins_client.list_jobs.return_value = [
            {"name": "test-job-1", "color": "blue"},
            {"name": "test-job-2", "color": "red"},
        ]
        mock_service_config.return_value.create_configured_jenkins_client.return_value = mock_jenkins_client

        response = client.get("/api/v1/jenkins/jobs")

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert "total" in data
        assert data["total"] == 2
        assert data["jobs"] == ["test-job-1", "test-job-2"]

    @patch("backend.api.routers.jenkins.ServiceClientCreators")
    def test_get_jenkins_jobs_with_search(self, mock_service_config, client):
        """Test Jenkins jobs retrieval with search query."""
        mock_jenkins_client = Mock()
        mock_jenkins_client.is_connected.return_value = True
        mock_jenkins_client.search_jobs.return_value = [{"name": "test-job-1", "color": "blue"}]
        mock_service_config.return_value.create_configured_jenkins_client.return_value = mock_jenkins_client

        response = client.get("/api/v1/jenkins/jobs?search=test")

        assert response.status_code == 200
        data = response.json()
        assert data["search_query"] == "test"
        assert data["total"] == 1

    @patch("backend.api.routers.jenkins.ServiceClientCreators")
    def test_get_jenkins_jobs_not_configured(self, mock_service_config, client):
        """Test Jenkins jobs when client is not configured."""
        mock_service_config.return_value.create_configured_jenkins_client.side_effect = ValueError(
            "Jenkins is not configured. Please provide URL, username, and API token in settings or as parameters."
        )

        response = client.get("/api/v1/jenkins/jobs")

        assert response.status_code == 503
        assert "Jenkins is not configured" in response.json()["detail"]

    @patch("backend.api.routers.jenkins.ServiceClientCreators")
    def test_get_jenkins_jobs_not_connected(self, mock_service_config, client):
        """Test Jenkins jobs when client is not connected."""
        mock_jenkins_client = Mock()
        mock_jenkins_client.is_connected.return_value = False
        mock_service_config.return_value.create_configured_jenkins_client.return_value = mock_jenkins_client

        response = client.get("/api/v1/jenkins/jobs")

        assert response.status_code == 503
        assert "Jenkins client connection failed" in response.json()["detail"]

    @patch("backend.api.routers.jenkins.ServiceClientCreators")
    def test_get_job_builds_success(self, mock_service_config, client):
        """Test successful retrieval of job builds."""
        mock_jenkins_client = Mock()
        mock_jenkins_client.is_connected.return_value = True
        mock_jenkins_client.get_job_builds.return_value = [
            {"number": 42, "result": "SUCCESS"},
            {"number": 41, "result": "FAILURE"},
        ]
        mock_service_config.return_value.create_configured_jenkins_client.return_value = mock_jenkins_client

        response = client.get("/api/v1/jenkins/test-job/builds")

        assert response.status_code == 200
        data = response.json()
        assert data["job_name"] == "test-job"
        assert len(data["builds"]) == 2
        assert data["limit"] == 10

    @patch("backend.api.routers.jenkins.ServiceClientCreators")
    def test_get_job_builds_with_limit(self, mock_service_config, client):
        """Test job builds retrieval with custom limit."""
        mock_jenkins_client = Mock()
        mock_jenkins_client.is_connected.return_value = True
        mock_jenkins_client.get_job_builds.return_value = [{"number": 42, "result": "SUCCESS"}]
        mock_service_config.return_value.create_configured_jenkins_client.return_value = mock_jenkins_client

        response = client.get("/api/v1/jenkins/test-job/builds?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 5


class TestStatusEndpoint:
    """Test the /api/v1/status endpoint."""

    @patch("backend.api.routers.system.BaseServiceConfig")
    @patch("backend.api.routers.system.ServiceClientCreators")
    @patch("backend.api.routers.system.ServiceStatusCheckers")
    def test_get_service_status_success(self, mock_status_checkers, mock_client_creators, mock_base_config, client):
        """Test successful service status retrieval."""
        # Mock status checkers
        mock_status_instance = Mock()
        mock_status_checkers.return_value = mock_status_instance
        mock_status_instance.get_service_status.return_value = {
            "jenkins": {"configured": True},
            "github": {"configured": True},
            "ai": {"configured": True},
        }

        # Mock client creators
        mock_creators_instance = Mock()
        mock_client_creators.return_value = mock_creators_instance

        # Mock Jenkins client
        mock_jenkins_client = Mock()
        mock_jenkins_client.is_connected.return_value = True
        mock_jenkins_client.url = FAKE_JENKINS_URL
        mock_creators_instance.create_configured_jenkins_client.return_value = mock_jenkins_client

        # Mock AI client (just needs to not raise exception)
        mock_creators_instance.create_configured_ai_client.return_value = Mock()

        # Mock base config
        mock_base_instance = Mock()
        mock_base_config.return_value = mock_base_instance
        mock_settings = Mock()
        mock_settings.last_updated = datetime.now()
        mock_base_instance.get_settings.return_value = mock_settings

        response = client.get("/api/v1/status")

        assert response.status_code == 200
        data = response.json()
        assert "services" in data
        assert "settings" in data
        assert data["services"]["jenkins"]["configured"] is True
        assert data["services"]["jenkins"]["available"] is True

    @patch("backend.api.routers.system.ServiceStatusCheckers")
    def test_get_service_status_jenkins_unavailable(self, mock_service_config, client):
        """Test service status when Jenkins is unavailable."""
        mock_service_config_instance = Mock()
        mock_service_config.return_value = mock_service_config_instance

        mock_service_config_instance.get_service_status.return_value = {
            "jenkins": {"configured": False},
            "github": {"configured": False},
            "ai": {"configured": False},
        }

        mock_service_config_instance.create_configured_jenkins_client.return_value = None
        mock_service_config_instance.create_configured_ai_client.side_effect = Exception("AI error")

        mock_settings = Mock()
        mock_settings.last_updated = None
        mock_service_config_instance.get_settings.return_value = mock_settings

        response = client.get("/api/v1/status")

        assert response.status_code == 200
        data = response.json()
        assert data["services"]["jenkins"]["available"] is False
        assert data["services"]["ai_analyzer"]["available"] is False


class TestAIModelsEndpoints:
    """Test AI models endpoints."""

    @patch("backend.api.routers.ai.ServiceClientCreators")
    def test_get_gemini_models_success(self, mock_service_client_creators, client):
        """Test successful Gemini models retrieval."""
        # Mock the ServiceClientCreators instance
        mock_creators_instance = Mock()
        mock_service_client_creators.return_value = mock_creators_instance

        # Mock the AI analyzer returned by create_configured_ai_client
        mock_ai_analyzer = Mock()
        mock_creators_instance.create_configured_ai_client.return_value = mock_ai_analyzer

        # Mock the underlying GeminiClient and its response
        mock_gemini_client = Mock()
        mock_ai_analyzer.client = mock_gemini_client

        mock_response = GeminiModelsResponse(
            success=True,
            models=[
                GeminiModelInfo(
                    name="gemini-1.5-pro",
                    display_name="Gemini 1.5 Pro",
                    description="Test model",
                    version="1.5",
                    input_token_limit=8192,
                    output_token_limit=8192,
                    supported_generation_methods=["generateContent"],
                )
            ],
            total_count=1,
            message="Success",
            error_details=None,
        )
        mock_gemini_client.get_available_models.return_value = mock_response

        response = client.post("/api/v1/ai/models?api_key=" + FAKE_GEMINI_API_KEY)  # pragma: allowlist secret

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["models"]) == 1

    @pytest.mark.parametrize(
        "error_message,error_details,api_key,expected_status,expected_detail_contains",
        [
            (
                "Authentication failed",
                "Invalid API key",
                FAKE_INVALID_API_KEY,
                401,
                "Authentication failed. Please verify your API key.",
            ),
            (
                "quota exceeded",
                "Rate limit exceeded",
                FAKE_GEMINI_API_KEY,
                429,
                "Rate limit exceeded",
            ),
        ],
    )
    @patch("backend.api.routers.ai.ServiceClientCreators")
    def test_get_gemini_models_error_scenarios(
        self,
        mock_service_client_creators,
        client,
        error_message,
        error_details,
        api_key,
        expected_status,
        expected_detail_contains,
    ):
        """Test Gemini models retrieval error scenarios."""
        # Mock the ServiceClientCreators instance
        mock_creators_instance = Mock()
        mock_service_client_creators.return_value = mock_creators_instance

        # Mock the AI analyzer returned by create_configured_ai_client
        mock_ai_analyzer = Mock()
        mock_creators_instance.create_configured_ai_client.return_value = mock_ai_analyzer

        # Mock the underlying GeminiClient and its response
        mock_gemini_client = Mock()
        mock_ai_analyzer.client = mock_gemini_client

        mock_response = GeminiModelsResponse(
            success=False,
            models=[],
            total_count=0,
            message=error_message,
            error_details=error_details,
        )
        mock_gemini_client.get_available_models.return_value = mock_response

        response = client.post(f"/api/v1/ai/models?api_key={api_key}")

        assert response.status_code == expected_status
        error_response = response.json()
        # Assert error payload shape - should have "detail" field, not "message"
        assert "detail" in error_response
        assert "message" not in error_response
        assert expected_detail_contains in error_response["detail"]

    @pytest.mark.parametrize(
        "client_side_effect,api_key,expected_status,expected_valid,expected_detail_contains",
        [
            (
                None,  # No exception - successful client creation
                FAKE_GEMINI_API_KEY,
                200,
                True,
                "API key format is valid and client initialized successfully",
            ),
            (
                ConnectionError("Invalid API key"),  # ConnectionError means invalid key
                FAKE_INVALID_API_KEY,
                503,
                None,  # No 'valid' field in error responses
                "Service unavailable",
            ),
            (
                TypeError("Non-string key"),  # TypeError for non-string keys
                FAKE_INVALID_API_KEY,
                400,
                None,  # No 'valid' field in error responses
                INVALID_API_KEY_FORMAT,
            ),
            (
                TimeoutError("Request timeout"),  # TimeoutError for timeout scenarios
                FAKE_GEMINI_API_KEY,
                504,
                None,  # No 'valid' field in error responses
                "Request timeout",
            ),
        ],
    )
    @patch("backend.api.routers.ai.ServiceClientCreators")
    def test_validate_gemini_api_key_scenarios(
        self,
        mock_service_client_creators,
        client,
        client_side_effect,
        api_key,
        expected_status,
        expected_valid,
        expected_detail_contains,
    ):
        """Test API key validation scenarios."""
        mock_creators_instance = Mock()
        mock_service_client_creators.return_value = mock_creators_instance

        if client_side_effect:
            mock_creators_instance.create_configured_ai_client.side_effect = client_side_effect
        else:
            # Mock successful client creation
            mock_ai_analyzer = Mock()
            mock_creators_instance.create_configured_ai_client.return_value = mock_ai_analyzer

        response = client.post(f"/api/v1/ai/models/validate-key?api_key={api_key}")

        assert response.status_code == expected_status
        data = response.json()

        if expected_valid is not None:
            assert data["valid"] is expected_valid

        if "detail" in data:
            assert expected_detail_contains in data["detail"]
        elif "message" in data:
            assert expected_detail_contains in data["message"]

        # Assert which key was used to ensure precedence and plumbing are correct
        if expected_status == 200:
            mock_creators_instance.create_configured_ai_client.assert_called_once_with(api_key=api_key)
        elif not client_side_effect:
            # For non-200 responses without side effects, the client creation should still be attempted
            mock_creators_instance.create_configured_ai_client.assert_called_once_with(api_key=api_key)

    def test_validate_key_precedence_non_string_body_validation(self, client):
        """Test that non-string body API key is properly rejected by FastAPI validation in validate-key."""
        response = client.post(
            f"/api/v1/ai/models/validate-key?api_key={FAKE_GEMINI_API_KEY}",  # Valid query parameter
            json={"api_key": 123},  # Non-string body should be rejected by Pydantic
        )
        # Should be 422 Pydantic validation error (expected behavior)
        assert response.status_code == 422
        data = response.json()
        assert isinstance(data["detail"], list)

    @patch("backend.api.routers.ai.ServiceClientCreators")
    def test_validate_key_precedence_empty_string_body_uses_query(self, mock_creators, client):
        """Test that empty string body API key doesn't override valid query parameter in validate-key."""
        # Mock the ServiceClientCreators instance and the full chain
        mock_creators_instance = Mock()
        mock_creators.return_value = mock_creators_instance

        # Mock successful client creation (just needs to not raise exception)
        mock_ai_analyzer = Mock()
        mock_creators_instance.create_configured_ai_client.return_value = mock_ai_analyzer

        response = client.post(
            f"/api/v1/ai/models/validate-key?api_key={FAKE_GEMINI_API_KEY}",  # Valid query parameter
            json={"api_key": ""},  # Empty body should not override
        )

        # Should succeed with mocked client
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "valid" in data["message"] and "initialized successfully" in data["message"]

        # Verify the mock was called with the query parameter, not empty string
        mock_creators_instance.create_configured_ai_client.assert_called_once_with(api_key=FAKE_GEMINI_API_KEY)


class TestSettingsEndpoints:
    """Test settings-related endpoints."""

    @patch("backend.api.routers.settings.SettingsService")
    def test_get_settings_success(self, mock_settings_service, client):
        """Test successful settings retrieval."""
        mock_service_instance = Mock()
        mock_settings_service.return_value = mock_service_instance

        mock_settings = AppSettings(
            jenkins=JenkinsSettings(
                url=FAKE_JENKINS_URL, username=FAKE_JENKINS_USERNAME, api_token=None, verify_ssl=True
            ),
            github=GitHubSettings(token="***masked***"),
            ai=AISettings(gemini_api_key="***masked***", model="", temperature=0.7, max_tokens=4096),
            last_updated=None,
        )
        mock_service_instance.get_masked_settings.return_value = mock_settings

        response = client.get("/api/v1/settings")

        assert response.status_code == 200
        data = response.json()
        assert "jenkins" in data
        assert "github" in data
        assert "ai" in data

    @patch("backend.api.routers.settings.SettingsService")
    def test_update_settings_success(self, mock_settings_service, client):
        """Test successful settings update."""
        mock_service_instance = Mock()
        mock_settings_service.return_value = mock_service_instance

        mock_updated_settings = AppSettings(
            jenkins=JenkinsSettings(
                url="https://new-jenkins.example.com", username="newuser", api_token=None, verify_ssl=True
            ),
            github=GitHubSettings(token="***masked***"),
            ai=AISettings(gemini_api_key="***masked***", model="", temperature=0.7, max_tokens=4096),
            last_updated=None,
        )
        mock_service_instance.get_masked_settings.return_value = mock_updated_settings

        settings_update = {"jenkins": {"url": "https://new-jenkins.example.com", "username": "newuser"}}

        response = client.put("/api/v1/settings", json=settings_update)

        assert response.status_code == 200
        data = response.json()
        assert data["jenkins"]["url"] == "https://new-jenkins.example.com"

    @patch("backend.api.routers.settings.SettingsService")
    def test_reset_settings_success(self, mock_settings_service, client):
        """Test successful settings reset."""
        mock_service_instance = Mock()
        mock_settings_service.return_value = mock_service_instance

        mock_default_settings = AppSettings(
            jenkins=JenkinsSettings(url=None, username=None, api_token=None, verify_ssl=True),
            github=GitHubSettings(token=None),
            ai=AISettings(gemini_api_key=None, model="", temperature=0.7, max_tokens=4096),
            last_updated=None,
        )
        mock_service_instance.get_masked_settings.return_value = mock_default_settings

        response = client.post("/api/v1/settings/reset")

        assert response.status_code == 200
        mock_service_instance.reset_settings.assert_called_once()

    @patch("backend.api.routers.settings.SettingsService")
    def test_validate_settings_success(self, mock_settings_service, client):
        """Test successful settings validation."""
        mock_service_instance = Mock()
        mock_settings_service.return_value = mock_service_instance

        mock_validation_result = {"jenkins": [], "github": [], "ai": []}
        mock_service_instance.validate_settings.return_value = mock_validation_result

        response = client.get("/api/v1/settings/validate")

        assert response.status_code == 200
        data = response.json()
        assert "jenkins" in data
        assert "github" in data
        assert "ai" in data

    @patch("backend.api.routers.settings.SettingsService")
    @patch("backend.api.routers.settings.ServiceConnectionTesters")
    def test_test_service_connection_jenkins_success(self, mock_connection_testers, mock_settings_service, client):
        """Test successful Jenkins connection test."""
        mock_settings_instance = Mock()
        mock_settings_service.return_value = mock_settings_instance

        mock_settings = Mock()
        mock_settings.jenkins.url = FAKE_JENKINS_URL
        mock_settings.jenkins.username = FAKE_JENKINS_USERNAME
        mock_settings.jenkins.api_token = FAKE_JENKINS_TOKEN
        mock_settings.jenkins.verify_ssl = True
        mock_settings_instance.get_settings.return_value = mock_settings

        mock_testers_instance = Mock()
        mock_connection_testers.return_value = mock_testers_instance
        # Mock the test_jenkins_connection method to not raise an exception
        mock_testers_instance.test_jenkins_connection.return_value = None

        response = client.post("/api/v1/settings/test-connection", params={"service": "jenkins"})

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "jenkins"
        assert data["success"] is True

    @patch("backend.api.routers.settings.SettingsService")
    @patch("backend.api.routers.settings.ServiceConnectionTesters")
    def test_test_service_connection_jenkins_failure(self, mock_connection_testers, mock_settings_service, client):
        """Test failed Jenkins connection test."""
        mock_settings_instance = Mock()
        mock_settings_service.return_value = mock_settings_instance

        mock_settings = Mock()
        mock_settings.jenkins.url = FAKE_JENKINS_URL
        mock_settings.jenkins.username = FAKE_JENKINS_USERNAME
        mock_settings.jenkins.api_token = FAKE_JENKINS_TOKEN
        mock_settings.jenkins.verify_ssl = True
        mock_settings_instance.get_settings.return_value = mock_settings

        mock_testers_instance = Mock()
        mock_connection_testers.return_value = mock_testers_instance
        mock_testers_instance.test_jenkins_connection.side_effect = ConnectionError("Connection failed")

        response = client.post("/api/v1/settings/test-connection", params={"service": "jenkins"})

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "jenkins"
        assert data["success"] is False
        assert "Connection failed" in data["message"]

    def test_test_service_connection_unknown_service(self, client):
        """Test connection test with unknown service."""
        response = client.post("/api/v1/settings/test-connection", params={"service": "unknown"})

        assert response.status_code == 400
        assert "Unknown service" in response.json()["detail"]

    @patch("backend.api.routers.settings.ServiceConnectionTesters")
    def test_test_service_connection_with_config_success(self, mock_connection_testers, client):
        """Test successful connection test with custom config."""
        mock_testers_instance = Mock()
        mock_connection_testers.return_value = mock_testers_instance
        # Mock the test_jenkins_connection method to not raise an exception
        mock_testers_instance.test_jenkins_connection.return_value = None

        request_data = {
            "service": "jenkins",
            "config": {
                "url": FAKE_JENKINS_URL,
                "username": FAKE_JENKINS_USERNAME,
                "api_token": FAKE_JENKINS_TOKEN,
                "verify_ssl": True,
            },
        }

        response = client.post("/api/v1/settings/test-connection-with-config", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "jenkins"
        assert data["success"] is True

    @patch("backend.api.routers.settings.SettingsService")
    def test_backup_settings_success(self, mock_settings_service, client):
        """Test successful settings backup."""
        mock_service_instance = Mock()
        mock_settings_service.return_value = mock_service_instance

        mock_settings = AppSettings(
            jenkins=JenkinsSettings(
                url=FAKE_JENKINS_URL, username=FAKE_JENKINS_USERNAME, api_token=None, verify_ssl=True
            ),
            github=GitHubSettings(token=FAKE_GITHUB_TOKEN),
            ai=AISettings(
                gemini_api_key=FAKE_GEMINI_API_KEY, model="", temperature=0.7, max_tokens=4096
            ),  # pragma: allowlist secret
            last_updated=None,
        )
        mock_service_instance.get_settings.return_value = mock_settings

        response = client.get("/api/v1/settings/backup")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "attachment" in response.headers.get("content-disposition", "")

    @patch("backend.api.routers.settings.SettingsService")
    def test_restore_settings_success(self, mock_settings_service, client):
        """Test successful settings restore."""
        mock_service_instance = Mock()
        mock_settings_service.return_value = mock_service_instance

        # Create a valid backup file content
        backup_data = {
            "jenkins": {
                "url": FAKE_JENKINS_URL,
                "username": FAKE_JENKINS_USERNAME,
                "api_token": None,
                "verify_ssl": True,
            },
            "github": {"token": FAKE_GITHUB_TOKEN},
            "ai": {
                "gemini_api_key": FAKE_GEMINI_API_KEY,
                "model": "",
                "temperature": 0.7,
                "max_tokens": 4096,
            },  # pragma: allowlist secret
        }
        backup_content = json.dumps(backup_data).encode("utf-8")

        mock_restored_settings = AppSettings(
            jenkins=JenkinsSettings(**backup_data["jenkins"]),
            github=GitHubSettings(**backup_data["github"]),
            ai=AISettings(**backup_data["ai"]),
            last_updated=None,
        )
        mock_service_instance.get_masked_settings.return_value = mock_restored_settings

        # Create a fake file upload using proper .json extension
        files = {"backup_file": ("settings_backup.json", BytesIO(backup_content), "application/json")}

        response = client.post("/api/v1/settings/restore", files=files)

        assert response.status_code == 200
        data = response.json()
        assert "jenkins" in data

    def test_restore_settings_invalid_file_type(self, client):
        """Test settings restore with invalid file type."""
        files = {"backup_file": ("settings.txt", BytesIO(b"invalid content"), "application/json")}

        response = client.post("/api/v1/settings/restore", files=files)

        assert response.status_code == 400
        assert "JSON file" in response.json()["detail"]

    def test_restore_settings_invalid_json(self, client):
        """Test settings restore with invalid JSON."""
        files = {"backup_file": ("settings.json", BytesIO(b"invalid json"), "application/json")}

        response = client.post("/api/v1/settings/restore", files=files)

        assert response.status_code == 400
        assert "Invalid JSON format" in response.json()["detail"]


class TestEndpointValidation:
    """Test endpoint parameter validation and edge cases."""

    def test_analyze_empty_text(self, client):
        """Test analyze endpoint with empty text."""
        response = client.post("/api/v1/analyze", data={"text": ""})
        # Should pass validation but might fail in processing
        assert response.status_code in [200, 500, 503]

    def test_jenkins_builds_invalid_limit(self, client):
        """Test Jenkins builds with invalid limit parameter."""
        response = client.get("/api/v1/jenkins/test-job/builds?limit=-1")
        assert response.status_code == 503  # Service unavailable because Jenkins not configured

    def test_gemini_models_invalid_api_key_length(self, client):
        """Test Gemini models with invalid API key length (format validation)."""
        # Use a key with valid prefix but wrong length to test length validation
        response = client.post("/api/v1/ai/models", json={"api_key": "AIzaSyShort"})
        assert response.status_code == 400
        assert INVALID_API_KEY_FORMAT in response.json()["detail"]

    def test_gemini_models_invalid_api_key_prefix(self, client):
        """Test Gemini models with invalid API key prefix (format validation)."""
        response = client.post("/api/v1/ai/models", json={"api_key": FAKE_INVALID_FORMAT_KEY})
        assert response.status_code == 400
        assert INVALID_API_KEY_FORMAT in response.json()["detail"]
        assert "AIzaSy" in response.json()["detail"]

    @pytest.mark.parametrize(
        "api_key,description",
        [
            ("  " + FAKE_GEMINI_API_KEY + "  ", "whitespace-padded valid key"),
            ("   ", "whitespace-only key"),
            ("  AIzaSyFakeKeyExample1234567890123456789  ", "whitespace-padded fake key"),  # gitleaks:allow
        ],
    )
    def test_gemini_models_whitespace_validation(self, client, api_key, description):
        """Test that whitespace-padded or whitespace-only API keys return authentication error."""
        response = client.post("/api/v1/ai/models", json={"api_key": api_key})
        assert response.status_code == 400
        assert FAILED_VALIDATE_AUTHENTICATION in response.json()["detail"]

    def test_gemini_models_non_string_api_key(self, client):
        """Test Gemini models with non-string API key."""
        # Test non-string body - should be rejected with validation error
        response = client.post("/api/v1/ai/models", json={"api_key": 123})
        assert response.status_code == 422
        data = response.json()
        # FastAPI validation errors return detail as a list
        assert isinstance(data["detail"], list)
        error_msg = str(data["detail"]).lower()
        assert "string" in error_msg or "type" in error_msg

    def test_api_key_precedence_non_string_body_validation(self, client):
        """Test that non-string body API key is properly rejected by FastAPI validation."""
        # This tests that FastAPI's Pydantic validation correctly rejects non-string types
        # before they reach our validation logic (which is expected behavior)
        response = client.post(
            f"/api/v1/ai/models?api_key={FAKE_GEMINI_API_KEY}",  # Valid query parameter
            json={"api_key": 123},  # Non-string body should be rejected by Pydantic
        )
        # Should be 422 Pydantic validation error (expected behavior)
        assert response.status_code == 422
        data = response.json()
        assert isinstance(data["detail"], list)

    @patch("backend.api.routers.ai.ServiceClientCreators")
    def test_api_key_precedence_string_body_overrides_query(self, mock_creators, client):
        """Test that valid string body API key properly overrides query parameter."""
        # Mock the ServiceClientCreators instance and the full chain
        mock_creators_instance = Mock()
        mock_creators.return_value = mock_creators_instance

        # Mock the AI analyzer and its client
        mock_ai_analyzer = Mock()
        mock_creators_instance.create_configured_ai_client.return_value = mock_ai_analyzer

        # Mock the underlying GeminiClient response
        mock_gemini_client = Mock()
        mock_ai_analyzer.client = mock_gemini_client

        mock_response = GeminiModelsResponse(
            success=True,
            models=[],
            total_count=0,
            message="Success",
            error_details=None,
        )
        mock_gemini_client.get_available_models.return_value = mock_response

        # Use an invalid query key but valid body key to test precedence
        response = client.post(
            "/api/v1/ai/models?api_key=invalid-query-key",
            json={"api_key": FAKE_GEMINI_API_KEY},  # Valid body should override
        )

        # Should succeed and use the body key, not the query key
        assert response.status_code == 200
        mock_creators_instance.create_configured_ai_client.assert_called_once_with(api_key=FAKE_GEMINI_API_KEY)

    @patch("backend.api.routers.ai.ServiceClientCreators")
    def test_api_key_precedence_empty_string_body_uses_query(self, mock_service_creators, client):
        """Test that empty string body API key doesn't override valid query parameter."""
        # Mock the service creators to make test deterministic
        mock_creators_instance = Mock()
        mock_service_creators.return_value = mock_creators_instance

        # Mock AI analyzer and client
        mock_ai_analyzer = Mock()
        mock_gemini_client = Mock()
        mock_creators_instance.create_configured_ai_client.return_value = mock_ai_analyzer
        mock_ai_analyzer.client = mock_gemini_client

        mock_response = GeminiModelsResponse(
            success=True,
            models=[],
            total_count=0,
            message="Success",
            error_details=None,
        )
        mock_gemini_client.get_available_models.return_value = mock_response

        response = client.post(
            f"/api/v1/ai/models?api_key={FAKE_GEMINI_API_KEY}",  # Valid query parameter
            json={"api_key": ""},  # Empty body should not override
        )
        # Should use query parameter and succeed deterministically
        assert response.status_code == 200
        mock_creators_instance.create_configured_ai_client.assert_called_once_with(api_key=FAKE_GEMINI_API_KEY)

    def test_settings_update_invalid_data(self, client):
        """Test settings update with invalid data."""
        response = client.put("/api/v1/settings", json={"invalid": "data"})
        # API is designed to accept and ignore invalid fields for flexibility
        assert response.status_code == 200

    def test_settings_update_accepts_partial_valid_data(self, client):
        """Test settings update accepts partial valid data."""
        # Test with a valid partial update
        response = client.put("/api/v1/settings", json={"jenkins": {"url": "https://example.com"}})
        # Should accept partial valid updates
        assert response.status_code == 200


class TestEndpointErrorHandling:
    """Test comprehensive error handling across endpoints."""

    @patch("backend.api.routers.jenkins.ServiceClientCreators")
    def test_jenkins_jobs_service_exception(self, mock_service_config, client):
        """Test Jenkins jobs endpoint with service exception."""
        mock_jenkins_client = Mock()
        mock_jenkins_client.is_connected.return_value = True
        mock_jenkins_client.list_jobs.side_effect = Exception("Service error")
        mock_service_config.return_value.create_configured_jenkins_client.return_value = mock_jenkins_client

        response = client.get("/api/v1/jenkins/jobs")

        assert response.status_code == 500
        assert "Failed to fetch Jenkins jobs" in response.json()["detail"]

    @patch("backend.api.routers.jenkins.ServiceClientCreators")
    def test_jenkins_builds_service_exception(self, mock_service_config, client):
        """Test Jenkins builds endpoint with service exception."""
        mock_jenkins_client = Mock()
        mock_jenkins_client.is_connected.return_value = True
        mock_jenkins_client.get_job_builds.side_effect = Exception("Service error")
        mock_service_config.return_value.create_configured_jenkins_client.return_value = mock_jenkins_client

        response = client.get("/api/v1/jenkins/test-job/builds")

        assert response.status_code == 500
        assert "Failed to get job builds" in response.json()["detail"]

    @patch("backend.api.routers.ai.ServiceClientCreators")
    def test_gemini_models_service_exception(self, mock_service_client_creators, client):
        """Test Gemini models endpoint with service exception."""
        mock_service_client_creators.side_effect = Exception("Service error")

        response = client.post("/api/v1/ai/models?api_key=" + FAKE_GEMINI_API_KEY)  # pragma: allowlist secret

        assert response.status_code == 500
        assert INTERNAL_SERVER_ERROR_FETCHING_MODELS in response.json()["detail"]

    @patch("backend.api.routers.settings.SettingsService")
    def test_settings_get_exception(self, mock_settings_service, client):
        """Test settings get endpoint with service exception."""
        mock_settings_service.side_effect = Exception("Settings error")

        response = client.get("/api/v1/settings")

        assert response.status_code == 500
        assert "Failed to retrieve settings" in response.json()["detail"]

    @patch("backend.api.routers.settings.SettingsService")
    def test_settings_update_exception(self, mock_settings_service, client):
        """Test settings update endpoint with service exception."""
        mock_service_instance = Mock()
        mock_settings_service.return_value = mock_service_instance
        mock_service_instance.update_settings.side_effect = Exception("Update error")

        response = client.put("/api/v1/settings", json={"jenkins": {"url": "test"}})

        assert response.status_code == 500
        assert "Failed to update settings" in response.json()["detail"]

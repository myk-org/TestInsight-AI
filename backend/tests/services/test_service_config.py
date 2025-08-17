"""Tests for ServiceConfig class."""

import pytest
from unittest.mock import Mock, patch

from backend.models.schemas import AppSettings, JenkinsSettings, GitHubSettings, AISettings, UserPreferences
from backend.services.service_config import ServiceConfig


class TestServiceConfig:
    """Test ServiceConfig factory methods and configuration."""

    @pytest.fixture
    def mock_app_settings(self):
        """Create mock AppSettings with test data."""
        return AppSettings(
            jenkins=JenkinsSettings(
                url="https://fake-jenkins.example.com",
                username="testuser",
                api_token="fake_token_123",
                verify_ssl=True,  # pragma: allowlist secret
            ),
            github=GitHubSettings(token="fake_github_token_xyz"),  # pragma: allowlist secret
            ai=AISettings(
                gemini_api_key="AIzaSyFakeKeyExample123456789",  # pragma: allowlist secret
                gemini_model="gemini-1.5-pro",
                temperature=0.7,
                max_tokens=4096,
            ),
            preferences=UserPreferences(),
        )

    @pytest.fixture
    def service_config(self, mock_app_settings):
        """Create ServiceConfig instance with mocked SettingsService."""
        with patch("backend.services.service_config.SettingsService") as mock_settings_service_class:
            mock_settings_service = Mock()
            mock_settings_service.get_settings.return_value = mock_app_settings
            mock_settings_service_class.return_value = mock_settings_service
            return ServiceConfig()

    def test_init(self, service_config):
        """Test ServiceConfig initialization."""
        assert service_config is not None

    def test_get_jenkins_config(self, service_config):
        """Test getting Jenkins configuration."""
        config = service_config.get_jenkins_config()
        assert config["url"] == "https://fake-jenkins.example.com"
        assert config["username"] == "testuser"
        assert config["password"] == "fake_token_123"  # pragma: allowlist secret
        assert config["verify_ssl"] is True

    def test_get_github_config(self, service_config):
        """Test getting GitHub configuration."""
        config = service_config.get_github_config()
        assert config["token"] == "fake_github_token_xyz"  # pragma: allowlist secret

    def test_get_ai_config(self, service_config):
        """Test getting AI configuration."""
        config = service_config.get_ai_config()
        assert config["api_key"] == "AIzaSyFakeKeyExample123456789"  # pragma: allowlist secret
        assert config["model"] == "gemini-1.5-pro"
        assert config["temperature"] == 0.7
        assert config["max_tokens"] == 4096

    @patch("backend.services.service_config.JenkinsClient")
    def test_create_configured_jenkins_client_with_settings(self, mock_jenkins_class, service_config):
        """Test creating Jenkins client using settings."""
        mock_client = Mock()
        mock_jenkins_class.return_value = mock_client

        client = service_config.create_configured_jenkins_client()

        mock_jenkins_class.assert_called_once_with(
            url="https://fake-jenkins.example.com",
            username="testuser",
            password="fake_token_123",  # pragma: allowlist secret
            verify_ssl=True,
        )
        assert client == mock_client

    @patch("backend.services.service_config.JenkinsClient")
    def test_create_configured_jenkins_client_with_args(self, mock_jenkins_class, service_config):
        """Test creating Jenkins client with provided arguments."""
        mock_client = Mock()
        mock_jenkins_class.return_value = mock_client

        client = service_config.create_configured_jenkins_client(
            url="https://other-jenkins.example.com",
            username="otheruser",
            password="other_token",  # pragma: allowlist secret
            verify_ssl=False,
        )

        mock_jenkins_class.assert_called_once_with(
            url="https://other-jenkins.example.com",
            username="otheruser",
            password="other_token",  # pragma: allowlist secret
            verify_ssl=False,
        )
        assert client == mock_client

    @patch("backend.services.service_config.JenkinsClient")
    def test_create_configured_jenkins_client_partial_args(self, mock_jenkins_class, service_config):
        """Test creating Jenkins client with partial arguments."""
        mock_client = Mock()
        mock_jenkins_class.return_value = mock_client

        client = service_config.create_configured_jenkins_client(url="https://override-jenkins.example.com")

        mock_jenkins_class.assert_called_once_with(
            url="https://override-jenkins.example.com",
            username="testuser",  # From settings
            password="fake_token_123",  # pragma: allowlist secret - From settings
            verify_ssl=True,  # From settings
        )
        assert client == mock_client

    @patch("backend.services.service_config.GeminiClient")
    @patch("backend.services.service_config.AIAnalyzer")
    def test_create_configured_ai_client_with_settings(self, mock_analyzer_class, mock_gemini_class, service_config):
        """Test creating AI client using settings."""
        mock_gemini_client = Mock()
        mock_gemini_class.return_value = mock_gemini_client
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        client = service_config.create_configured_ai_client()

        mock_gemini_class.assert_called_once_with(api_key="AIzaSyFakeKeyExample123456789")  # pragma: allowlist secret
        mock_analyzer_class.assert_called_once_with(client=mock_gemini_client)
        assert client == mock_analyzer

    @patch("backend.services.service_config.GeminiClient")
    @patch("backend.services.service_config.AIAnalyzer")
    def test_create_configured_ai_client_with_args(self, mock_analyzer_class, mock_gemini_class, service_config):
        """Test creating AI client with provided arguments."""
        mock_gemini_client = Mock()
        mock_gemini_class.return_value = mock_gemini_client
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        client = service_config.create_configured_ai_client(
            api_key="AIzaSyCustomKeyExample123"  # pragma: allowlist secret
        )

        mock_gemini_class.assert_called_once_with(api_key="AIzaSyCustomKeyExample123")  # pragma: allowlist secret
        mock_analyzer_class.assert_called_once_with(client=mock_gemini_client)
        assert client == mock_analyzer

    @patch("backend.services.service_config.GeminiClient")
    @patch("backend.services.service_config.AIAnalyzer")
    def test_create_configured_ai_client_no_api_key(self, mock_analyzer_class, mock_gemini_class):
        """Test creating AI client with no API key raises error."""
        # Create empty AI settings
        empty_settings = AppSettings(ai=AISettings(gemini_api_key=""))

        with patch("backend.services.service_config.SettingsService") as mock_settings_service_class:
            mock_settings_service = Mock()
            mock_settings_service.get_settings.return_value = empty_settings
            mock_settings_service_class.return_value = mock_settings_service
            service_config = ServiceConfig()

            with pytest.raises(ValueError, match="AI service is not configured"):
                service_config.create_configured_ai_client()

    @patch("backend.services.service_config.GitClient")
    def test_create_configured_git_client_with_settings(self, mock_git_class, service_config):
        """Test creating Git client using settings."""
        mock_client = Mock()
        mock_git_class.return_value = mock_client

        client = service_config.create_configured_git_client(repo_url="https://github.com/testorg/testrepo")

        mock_git_class.assert_called_once_with(
            repo_url="https://github.com/testorg/testrepo",
            branch=None,
            commit=None,
            github_token="fake_github_token_xyz",  # pragma: allowlist secret,
        )
        assert client == mock_client

    @patch("backend.services.service_config.GitClient")
    def test_create_configured_git_client_with_args(self, mock_git_class, service_config):
        """Test creating Git client with provided arguments."""
        mock_client = Mock()
        mock_git_class.return_value = mock_client

        client = service_config.create_configured_git_client(
            repo_url="https://github.com/testorg/testrepo", branch="develop", github_token="custom_token_xyz"
        )

        mock_git_class.assert_called_once_with(
            repo_url="https://github.com/testorg/testrepo",
            branch="develop",
            commit=None,
            github_token="custom_token_xyz",
        )
        assert client == mock_client

    @patch("backend.services.service_config.GitClient")
    def test_create_configured_git_client_no_repo_url(self, mock_git_class, service_config):
        """Test creating Git client without repo URL raises error."""
        with pytest.raises(ValueError, match="repo_url is required"):
            service_config.create_configured_git_client(repo_url="")

    @patch("backend.services.service_config.JenkinsClient")
    def test_test_jenkins_connection_success(self, mock_jenkins_class, service_config):
        """Test successful Jenkins connection test."""
        mock_client = Mock()
        mock_client.is_connected.return_value = True
        mock_jenkins_class.return_value = mock_client

        result = service_config.test_jenkins_connection(
            url="https://test-jenkins.example.com",
            username="testuser",
            password="test_token",  # pragma: allowlist secret
            verify_ssl=False,  # pragma: allowlist secret
        )

        assert result is True
        mock_jenkins_class.assert_called_once_with(
            url="https://test-jenkins.example.com",
            username="testuser",
            password="test_token",  # pragma: allowlist secret
            verify_ssl=False,
        )

    @patch("backend.services.service_config.JenkinsClient")
    def test_test_jenkins_connection_failure(self, mock_jenkins_class, service_config):
        """Test failed Jenkins connection test."""
        mock_client = Mock()
        mock_client.is_connected.return_value = False
        mock_jenkins_class.return_value = mock_client

        with pytest.raises(ConnectionError, match="Jenkins connection failed"):
            service_config.test_jenkins_connection(
                url="https://bad-jenkins.example.com",
                username="testuser",
                password="bad_token",  # pragma: allowlist secret
            )

    @patch("backend.services.service_config.JenkinsClient")
    def test_test_jenkins_connection_exception(self, mock_jenkins_class, service_config):
        """Test Jenkins connection test with exception."""
        mock_jenkins_class.side_effect = Exception("Connection error")

        with pytest.raises(ConnectionError, match="Jenkins connection error"):
            service_config.test_jenkins_connection(
                url="https://error-jenkins.example.com",
                username="testuser",
                password="test_token",  # pragma: allowlist secret
            )

    @patch("backend.services.service_config.requests.get")
    def test_test_github_connection_success(self, mock_get, service_config):
        """Test successful GitHub connection test."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"login": "testuser"}
        mock_get.return_value = mock_response

        result = service_config.test_github_connection(token="fake_github_token")

        assert result is True
        mock_get.assert_called_once()

    @patch("backend.services.service_config.requests.get")
    def test_test_github_connection_failure(self, mock_get, service_config):
        """Test failed GitHub connection test."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Bad credentials"
        mock_get.return_value = mock_response

        with pytest.raises(ConnectionError, match="GitHub API error"):
            service_config.test_github_connection(token="bad_token")

    @patch("backend.services.service_config.requests.get")
    def test_test_github_connection_exception(self, mock_get, service_config):
        """Test GitHub connection test with exception."""
        mock_get.side_effect = Exception("Network error")

        with pytest.raises(ConnectionError, match="GitHub connection error"):
            service_config.test_github_connection(token="test_token")  # pragma: allowlist secret

    @patch("backend.services.service_config.GeminiClient")
    def test_test_ai_connection_success(self, mock_gemini_class, service_config):
        """Test successful AI connection test."""
        mock_client = Mock()
        mock_gemini_class.return_value = mock_client

        result = service_config.test_ai_connection(api_key="AIzaSyTestKey123")  # pragma: allowlist secret

        assert result is True
        mock_gemini_class.assert_called_once_with(api_key="AIzaSyTestKey123")  # pragma: allowlist secret

    @patch("backend.services.service_config.GeminiClient")
    def test_test_ai_connection_failure(self, mock_gemini_class, service_config):
        """Test failed AI connection test."""
        mock_gemini_class.side_effect = Exception("Invalid API key")

        with pytest.raises(ConnectionError, match="AI service connection error"):
            service_config.test_ai_connection(api_key="invalid_key")  # pragma: allowlist secret

    @patch("backend.services.service_config.GeminiClient")
    def test_test_ai_connection_exception(self, mock_gemini_class, service_config):
        """Test AI connection test with exception."""
        mock_gemini_class.side_effect = Exception("API error")

        with pytest.raises(ConnectionError, match="AI service connection error"):
            service_config.test_ai_connection(api_key="test_key")  # pragma: allowlist secret

    def test_get_user_preferences(self, service_config):
        """Test getting user preferences."""
        preferences = service_config.get_user_preferences()
        assert preferences["theme"] == "system"
        assert preferences["language"] == "en"
        assert preferences["auto_refresh"] is True
        assert preferences["results_per_page"] == 10

    def test_is_jenkins_configured(self, service_config):
        """Test Jenkins configuration check."""
        assert service_config.is_jenkins_configured() is True

    def test_is_jenkins_not_configured(self):
        """Test Jenkins not configured."""
        empty_settings = AppSettings(jenkins=JenkinsSettings(url="", username="", api_token=""))

        with patch("backend.services.service_config.SettingsService") as mock_settings_service_class:
            mock_settings_service = Mock()
            mock_settings_service.get_settings.return_value = empty_settings
            mock_settings_service_class.return_value = mock_settings_service
            service_config = ServiceConfig()

            assert service_config.is_jenkins_configured() is False

    def test_is_github_configured(self, service_config):
        """Test GitHub configuration check."""
        assert service_config.is_github_configured() is True

    def test_is_github_not_configured(self):
        """Test GitHub not configured."""
        empty_settings = AppSettings(github=GitHubSettings(token=""))

        with patch("backend.services.service_config.SettingsService") as mock_settings_service_class:
            mock_settings_service = Mock()
            mock_settings_service.get_settings.return_value = empty_settings
            mock_settings_service_class.return_value = mock_settings_service
            service_config = ServiceConfig()

            assert service_config.is_github_configured() is False

    def test_is_ai_configured(self, service_config):
        """Test AI configuration check."""
        assert service_config.is_ai_configured() is True

    def test_is_ai_not_configured(self):
        """Test AI not configured."""
        empty_settings = AppSettings(ai=AISettings(gemini_api_key=""))

        with patch("backend.services.service_config.SettingsService") as mock_settings_service_class:
            mock_settings_service = Mock()
            mock_settings_service.get_settings.return_value = empty_settings
            mock_settings_service_class.return_value = mock_settings_service
            service_config = ServiceConfig()

            assert service_config.is_ai_configured() is False

    def test_get_service_status(self, service_config):
        """Test getting service status."""
        status = service_config.get_service_status()

        assert "jenkins" in status
        assert "github" in status
        assert "ai" in status

        assert status["jenkins"]["configured"] is True
        assert status["github"]["configured"] is True
        assert status["ai"]["configured"] is True

        # Check config structure
        jenkins_config = status["jenkins"]["config"]
        assert jenkins_config["url"] is True  # boolean representation of non-empty string
        assert jenkins_config["username"] is True
        assert jenkins_config["password"] is True
        assert jenkins_config["verify_ssl"] is True

        github_config = status["github"]["config"]
        assert github_config["token"] is True

        ai_config = status["ai"]["config"]
        assert ai_config["api_key"] is True
        assert ai_config["model"] == "gemini-1.5-pro"
        assert ai_config["temperature"] == 0.7
        assert ai_config["max_tokens"] == 4096

    def test_get_settings(self, service_config, mock_app_settings):
        """Test getting settings."""
        settings = service_config.get_settings()
        assert settings == mock_app_settings
        assert settings.jenkins.url == "https://fake-jenkins.example.com"
        assert settings.github.token == "fake_github_token_xyz"  # pragma: allowlist secret
        assert settings.ai.gemini_api_key == "AIzaSyFakeKeyExample123456789"  # pragma: allowlist secret

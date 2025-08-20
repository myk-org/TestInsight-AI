"""Tests for ServiceConfig class."""

import pytest
from unittest.mock import Mock, patch

from backend.models.schemas import AppSettings, JenkinsSettings, GitHubSettings, AISettings
from backend.services.service_config.client_creators import ServiceClientCreators
from backend.services.service_config.connection_testers import ServiceConnectionTesters
from backend.services.service_config.status_checkers import ServiceStatusCheckers
from backend.services.service_config.config_getters import ServiceConfigGetters
from backend.tests.conftest import (
    FAKE_BAD_TOKEN,
    FAKE_CUSTOM_API_KEY,
    FAKE_CUSTOM_TOKEN,
    FAKE_GEMINI_API_KEY,
    FAKE_GITHUB_TOKEN,
    FAKE_INVALID_API_KEY,
    FAKE_JENKINS_TOKEN,
    FAKE_OTHER_TOKEN,
    FAKE_TEST_TOKEN,
)


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
                model="gemini-1.5-pro",
                temperature=0.7,
                max_tokens=4096,
            ),
        )

    @pytest.fixture
    def service_config_getters(self, mock_app_settings):
        """Create ServiceConfigGetters instance with mocked SettingsService."""
        with patch("backend.services.service_config.base.SettingsService") as mock_settings_service_class:
            mock_settings_service = Mock()
            mock_settings_service.get_settings.return_value = mock_app_settings
            mock_settings_service_class.return_value = mock_settings_service
            yield ServiceConfigGetters()

    @pytest.fixture
    def service_client_creators(self, mock_app_settings):
        """Create ServiceClientCreators instance with mocked SettingsService."""
        with patch("backend.services.service_config.base.SettingsService") as mock_settings_service_class:
            mock_settings_service = Mock()
            mock_settings_service.get_settings.return_value = mock_app_settings
            mock_settings_service_class.return_value = mock_settings_service
            yield ServiceClientCreators()

    @pytest.fixture
    def service_connection_testers(self, mock_app_settings):
        """Create ServiceConnectionTesters instance with mocked SettingsService."""
        with patch("backend.services.service_config.base.SettingsService") as mock_settings_service_class:
            mock_settings_service = Mock()
            mock_settings_service.get_settings.return_value = mock_app_settings
            mock_settings_service_class.return_value = mock_settings_service
            yield ServiceConnectionTesters()

    @pytest.fixture
    def service_status_checkers(self, mock_app_settings):
        """Create ServiceStatusCheckers instance with mocked SettingsService."""
        with patch("backend.services.service_config.base.SettingsService") as mock_settings_service_class:
            mock_settings_service = Mock()
            mock_settings_service.get_settings.return_value = mock_app_settings
            mock_settings_service_class.return_value = mock_settings_service
            yield ServiceStatusCheckers()

    def test_init_getters(self, service_config_getters):
        """Test ServiceConfigGetters initialization."""
        assert service_config_getters is not None

    def test_get_jenkins_config(self, service_config_getters):
        """Test getting Jenkins configuration."""
        config = service_config_getters.get_jenkins_config()
        assert config["url"] == "https://fake-jenkins.example.com"
        assert config["username"] == "testuser"
        assert config["password"] == FAKE_JENKINS_TOKEN
        assert config["verify_ssl"] is True

    def test_get_github_config(self, service_config_getters):
        """Test getting GitHub configuration."""
        config = service_config_getters.get_github_config()
        assert config["token"] == FAKE_GITHUB_TOKEN

    def test_get_ai_config(self, service_config_getters):
        """Test getting AI configuration."""
        config = service_config_getters.get_ai_config()
        assert config["api_key"] == FAKE_GEMINI_API_KEY
        assert config["model"] == "gemini-1.5-pro"
        assert config["temperature"] == 0.7
        assert config["max_tokens"] == 4096

    def test_create_configured_jenkins_client_with_settings(self, service_client_creators):
        """Test creating Jenkins client using settings."""
        with patch("backend.services.service_config.client_creators.JenkinsClient") as mock_jenkins_class:
            mock_client = Mock()
            mock_jenkins_class.return_value = mock_client

            client = service_client_creators.create_configured_jenkins_client()

            mock_jenkins_class.assert_called_once_with(
                url="https://fake-jenkins.example.com",
                username="testuser",
                password=FAKE_JENKINS_TOKEN,
                verify_ssl=True,
            )
            assert client == mock_client

    @patch("backend.services.service_config.client_creators.JenkinsClient")
    def test_create_configured_jenkins_client_with_args(self, mock_jenkins_class, service_client_creators):
        """Test creating Jenkins client with provided arguments."""
        mock_client = Mock()
        mock_jenkins_class.return_value = mock_client

        client = service_client_creators.create_configured_jenkins_client(
            url="https://other-jenkins.example.com",
            username="otheruser",
            password=FAKE_OTHER_TOKEN,
            verify_ssl=False,
        )

        mock_jenkins_class.assert_called_once_with(
            url="https://other-jenkins.example.com",
            username="otheruser",
            password=FAKE_OTHER_TOKEN,
            verify_ssl=False,
        )
        assert client == mock_client

    def test_create_configured_jenkins_client_partial_args(self, service_client_creators):
        """Test creating Jenkins client with partial arguments."""
        with patch("backend.services.service_config.client_creators.JenkinsClient") as mock_jenkins_class:
            mock_client = Mock()
            mock_jenkins_class.return_value = mock_client

            client = service_client_creators.create_configured_jenkins_client(
                url="https://override-jenkins.example.com"
            )

            mock_jenkins_class.assert_called_once_with(
                url="https://override-jenkins.example.com",
                username="testuser",  # From settings
                password=FAKE_JENKINS_TOKEN,  # From settings
                verify_ssl=True,  # From settings
            )
            assert client == mock_client

    def test_create_configured_ai_client_with_settings(self, service_client_creators):
        """Test creating AI client using settings."""
        with (
            patch("backend.services.service_config.client_creators.GeminiClient") as mock_gemini_class,
            patch("backend.services.service_config.client_creators.AIAnalyzer") as mock_analyzer_class,
        ):
            mock_gemini_client = Mock()
            mock_gemini_class.return_value = mock_gemini_client
            mock_analyzer = Mock()
            mock_analyzer_class.return_value = mock_analyzer

            client = service_client_creators.create_configured_ai_client()

            mock_gemini_class.assert_called_once_with(api_key=FAKE_GEMINI_API_KEY)
            mock_analyzer_class.assert_called_once_with(client=mock_gemini_client)
            assert client == mock_analyzer

    @patch("backend.services.service_config.client_creators.GeminiClient")
    @patch("backend.services.service_config.client_creators.AIAnalyzer")
    def test_create_configured_ai_client_with_args(
        self, mock_analyzer_class, mock_gemini_class, service_client_creators
    ):
        """Test creating AI client with provided arguments."""
        mock_gemini_client = Mock()
        mock_gemini_class.return_value = mock_gemini_client
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        client = service_client_creators.create_configured_ai_client(api_key=FAKE_CUSTOM_API_KEY)

        mock_gemini_class.assert_called_once_with(api_key=FAKE_CUSTOM_API_KEY)
        mock_analyzer_class.assert_called_once_with(client=mock_gemini_client)
        assert client == mock_analyzer

    @patch("backend.services.service_config.client_creators.GeminiClient")
    @patch("backend.services.service_config.client_creators.AIAnalyzer")
    def test_create_configured_ai_client_no_api_key(self, mock_analyzer_class, mock_gemini_class):
        """Test creating AI client with no API key raises error."""
        # Create empty AI settings
        empty_settings = AppSettings(ai=AISettings(gemini_api_key=""))

        with patch("backend.services.service_config.base.SettingsService") as mock_settings_service_class:
            mock_settings_service = Mock()
            mock_settings_service.get_settings.return_value = empty_settings
            mock_settings_service_class.return_value = mock_settings_service
            service_client_creators = ServiceClientCreators()

            with pytest.raises(ValueError, match="AI service is not configured"):
                service_client_creators.create_configured_ai_client()

    def test_create_configured_git_client_with_settings(self, service_client_creators):
        """Test creating Git client using settings."""
        with patch("backend.services.service_config.client_creators.GitClient") as mock_git_class:
            mock_client = Mock()
            mock_git_class.return_value = mock_client

            client = service_client_creators.create_configured_git_client(
                repo_url="https://github.com/testorg/testrepo"
            )

            mock_git_class.assert_called_once_with(
                repo_url="https://github.com/testorg/testrepo",
                branch=None,
                commit=None,
                github_token=FAKE_GITHUB_TOKEN,
            )
            assert client == mock_client

    @patch("backend.services.service_config.client_creators.GitClient")
    def test_create_configured_git_client_with_args(self, mock_git_class, service_client_creators):
        """Test creating Git client with provided arguments."""
        mock_client = Mock()
        mock_git_class.return_value = mock_client

        client = service_client_creators.create_configured_git_client(
            repo_url="https://github.com/testorg/testrepo", branch="develop", github_token="custom_token_xyz"
        )

        mock_git_class.assert_called_once_with(
            repo_url="https://github.com/testorg/testrepo",
            branch="develop",
            commit=None,
            github_token=FAKE_CUSTOM_TOKEN,
        )
        assert client == mock_client

    @patch("backend.services.service_config.client_creators.GitClient")
    def test_create_configured_git_client_no_repo_url(self, mock_git_class, service_client_creators):
        """Test creating Git client without repo URL raises error."""
        with pytest.raises(ValueError, match="repo_url is required"):
            service_client_creators.create_configured_git_client(repo_url="")

    @patch("backend.services.service_config.connection_testers.ServiceClientCreators")
    def test_test_jenkins_connection_success(self, mock_client_creators_class, service_connection_testers):
        """Test successful Jenkins connection test."""
        mock_client_creators = Mock()
        mock_jenkins_client = Mock()
        mock_jenkins_client.is_connected.return_value = True
        mock_client_creators.create_configured_jenkins_client.return_value = mock_jenkins_client
        mock_client_creators_class.return_value = mock_client_creators

        result = service_connection_testers.test_jenkins_connection(
            url="https://test-jenkins.example.com",
            username="testuser",
            password=FAKE_TEST_TOKEN,
            verify_ssl=False,  # pragma: allowlist secret
        )

        assert result is True
        mock_client_creators.create_configured_jenkins_client.assert_called_once_with(
            url="https://test-jenkins.example.com",
            username="testuser",
            password=FAKE_TEST_TOKEN,
            verify_ssl=False,
        )

    @patch("backend.services.service_config.connection_testers.ServiceClientCreators")
    def test_test_jenkins_connection_failure(self, mock_client_creators_class, service_connection_testers):
        """Test failed Jenkins connection test."""
        mock_client_creators = Mock()
        mock_jenkins_client = Mock()
        mock_jenkins_client.is_connected.return_value = False
        mock_client_creators.create_configured_jenkins_client.return_value = mock_jenkins_client
        mock_client_creators_class.return_value = mock_client_creators

        with pytest.raises(ConnectionError, match="Jenkins connection failed"):
            service_connection_testers.test_jenkins_connection(
                url="https://bad-jenkins.example.com",
                username="testuser",
                password=FAKE_BAD_TOKEN,
            )

    @patch("backend.services.service_config.connection_testers.ServiceClientCreators")
    def test_test_jenkins_connection_exception(self, mock_client_creators_class, service_connection_testers):
        """Test Jenkins connection test with exception."""
        mock_client_creators_class.side_effect = Exception("Connection error")

        with pytest.raises(ConnectionError, match="Jenkins connection error"):
            service_connection_testers.test_jenkins_connection(
                url="https://error-jenkins.example.com",
                username="testuser",
                password=FAKE_TEST_TOKEN,
            )

    @patch("backend.services.service_config.connection_testers.requests.get")
    def test_test_github_connection_success(self, mock_get, service_connection_testers):
        """Test successful GitHub connection test."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"login": "testuser"}
        mock_get.return_value = mock_response

        result = service_connection_testers.test_github_connection(token=FAKE_GITHUB_TOKEN)

        assert result is True
        mock_get.assert_called_once()

    @patch("backend.services.service_config.connection_testers.requests.get")
    def test_test_github_connection_failure(self, mock_get, service_connection_testers):
        """Test failed GitHub connection test."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Bad credentials"
        mock_get.return_value = mock_response

        with pytest.raises(ConnectionError, match="GitHub API error"):
            service_connection_testers.test_github_connection(token=FAKE_BAD_TOKEN)

    @patch("backend.services.service_config.connection_testers.requests.get")
    def test_test_github_connection_exception(self, mock_get, service_connection_testers):
        """Test GitHub connection test with exception."""
        mock_get.side_effect = Exception("Network error")

        with pytest.raises(ConnectionError, match="GitHub connection error"):
            service_connection_testers.test_github_connection(token=FAKE_TEST_TOKEN)

    @patch("backend.services.service_config.connection_testers.ServiceClientCreators")
    def test_test_ai_connection_success(self, mock_client_creators_class, service_connection_testers):
        """Test successful AI connection test."""
        mock_client_creators = Mock()
        mock_ai_client = Mock()
        mock_client_creators.create_configured_ai_client.return_value = mock_ai_client
        mock_client_creators_class.return_value = mock_client_creators

        result = service_connection_testers.test_ai_connection(api_key=FAKE_CUSTOM_API_KEY)

        assert result is True
        mock_client_creators.create_configured_ai_client.assert_called_once_with(api_key=FAKE_CUSTOM_API_KEY)

    @patch("backend.services.service_config.connection_testers.ServiceClientCreators")
    def test_test_ai_connection_failure(self, mock_client_creators_class, service_connection_testers):
        """Test failed AI connection test."""
        mock_client_creators_class.side_effect = Exception("Invalid API key")

        with pytest.raises(ConnectionError, match="AI service connection error"):
            service_connection_testers.test_ai_connection(api_key=FAKE_INVALID_API_KEY)

    @patch("backend.services.service_config.connection_testers.ServiceClientCreators")
    def test_test_ai_connection_exception(self, mock_client_creators_class, service_connection_testers):
        """Test AI connection test with exception."""
        mock_client_creators_class.side_effect = Exception("API error")

        with pytest.raises(ConnectionError, match="AI service connection error"):
            service_connection_testers.test_ai_connection(api_key=FAKE_TEST_TOKEN)

    def test_is_jenkins_configured(self, service_status_checkers):
        """Test Jenkins configuration check."""
        assert service_status_checkers.is_jenkins_configured() is True

    def test_is_jenkins_not_configured(self):
        """Test Jenkins not configured."""
        empty_settings = AppSettings(jenkins=JenkinsSettings(url="", username="", api_token=""))

        with patch("backend.services.service_config.base.SettingsService") as mock_settings_service_class:
            mock_settings_service = Mock()
            mock_settings_service.get_settings.return_value = empty_settings
            mock_settings_service_class.return_value = mock_settings_service
            from backend.services.service_config.status_checkers import ServiceStatusCheckers

            service_status_checkers = ServiceStatusCheckers()

            assert service_status_checkers.is_jenkins_configured() is False

    def test_is_github_configured(self, service_status_checkers):
        """Test GitHub configuration check."""
        assert service_status_checkers.is_github_configured() is True

    def test_is_github_not_configured(self):
        """Test GitHub not configured."""
        empty_settings = AppSettings(github=GitHubSettings(token=""))

        with patch("backend.services.service_config.base.SettingsService") as mock_settings_service_class:
            mock_settings_service = Mock()
            mock_settings_service.get_settings.return_value = empty_settings
            mock_settings_service_class.return_value = mock_settings_service
            from backend.services.service_config.status_checkers import ServiceStatusCheckers

            service_status_checkers = ServiceStatusCheckers()

            assert service_status_checkers.is_github_configured() is False

    def test_is_ai_configured(self, service_status_checkers):
        """Test AI configuration check."""
        assert service_status_checkers.is_ai_configured() is True

    def test_is_ai_not_configured(self):
        """Test AI not configured."""
        empty_settings = AppSettings(ai=AISettings(gemini_api_key=""))

        with patch("backend.services.service_config.base.SettingsService") as mock_settings_service_class:
            mock_settings_service = Mock()
            mock_settings_service.get_settings.return_value = empty_settings
            mock_settings_service_class.return_value = mock_settings_service
            from backend.services.service_config.status_checkers import ServiceStatusCheckers

            service_status_checkers = ServiceStatusCheckers()

            assert service_status_checkers.is_ai_configured() is False

    def test_get_service_status(self, service_status_checkers):
        """Test getting service status."""
        status = service_status_checkers.get_service_status()

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

    def test_get_settings(self, service_config_getters, mock_app_settings):
        """Test getting settings."""
        settings = service_config_getters.get_settings()
        assert settings == mock_app_settings
        assert settings.jenkins.url == "https://fake-jenkins.example.com"
        assert settings.github.token == FAKE_GITHUB_TOKEN
        assert settings.ai.gemini_api_key == FAKE_GEMINI_API_KEY

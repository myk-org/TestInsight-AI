"""Service configuration manager for TestInsight AI."""

import requests

from backend.models.schemas import AppSettings
from backend.services.ai_analyzer import AIAnalyzer
from backend.services.gemini_api import GeminiClient
from backend.services.git_client import GitClient
from backend.services.jenkins_client import JenkinsClient
from backend.services.settings_service import SettingsService


class ServiceConfig:
    """Centralized service configuration using settings."""

    def __init__(self) -> None:
        """Initialize service configuration."""
        self._settings_service = SettingsService()

    def get_settings(self) -> AppSettings:
        """Get current settings (always fresh).

        Returns:
            Current application settings
        """
        return self._settings_service.get_settings()

    def get_jenkins_config(self) -> dict[str, str | bool]:
        """Get Jenkins configuration.

        Returns:
            Dictionary with Jenkins connection parameters
        """
        settings = self.get_settings()

        return {
            "url": settings.jenkins.url or "",
            "username": settings.jenkins.username or "",
            "password": settings.jenkins.api_token or "",
            "verify_ssl": settings.jenkins.verify_ssl,
        }

    def get_github_config(self) -> dict[str, str | None]:
        """Get GitHub configuration.

        Returns:
            Dictionary with GitHub connection parameters
        """
        settings = self.get_settings()

        return {"token": settings.github.token}

    def get_ai_config(self) -> dict[str, str | float | int | None]:
        """Get AI service configuration.

        Returns:
            Dictionary with AI service parameters
        """
        settings = self.get_settings()

        return {
            "api_key": settings.ai.gemini_api_key or "",
            "model": settings.ai.gemini_model.value if settings.ai.gemini_model else "",
            "temperature": settings.ai.temperature,
            "max_tokens": settings.ai.max_tokens,
        }

    def get_user_preferences(self) -> dict[str, str | bool | int]:
        """Get user preferences.

        Returns:
            Dictionary with user preferences
        """
        settings = self.get_settings()

        return {
            "theme": settings.preferences.theme,
            "language": settings.preferences.language,
            "auto_refresh": settings.preferences.auto_refresh,
            "results_per_page": settings.preferences.results_per_page,
        }

    def is_jenkins_configured(self) -> bool:
        """Check if Jenkins is properly configured.

        Returns:
            True if Jenkins has all required configuration
        """
        config = self.get_jenkins_config()
        return bool(config["url"] and config["username"] and config["password"])

    def is_github_configured(self) -> bool:
        """Check if GitHub is properly configured.

        Returns:
            True if GitHub has required configuration
        """
        config = self.get_github_config()
        return bool(config["token"])

    def is_ai_configured(self) -> bool:
        """Check if AI service is properly configured.

        Returns:
            True if AI service has required configuration
        """
        config = self.get_ai_config()
        return bool(config["api_key"])

    def get_service_status(self) -> dict[str, dict[str, bool | dict[str, str | bool | float | int]]]:
        """Get configuration status for all services.

        Returns:
            Dictionary with service configuration status
        """
        return {
            "jenkins": {
                "configured": self.is_jenkins_configured(),
                "config": {k: bool(v) if k != "verify_ssl" else v for k, v in self.get_jenkins_config().items()},
            },
            "github": {
                "configured": self.is_github_configured(),
                "config": {k: bool(v) for k, v in self.get_github_config().items()},
            },
            "ai": {
                "configured": self.is_ai_configured(),
                "config": {
                    "api_key": bool(self.get_ai_config()["api_key"]),
                    "model": self.get_ai_config()["model"] or "",
                    "temperature": float(self.get_ai_config()["temperature"] or 0.7),
                    "max_tokens": int(self.get_ai_config()["max_tokens"] or 4096),
                },
            },
        }

    def create_configured_jenkins_client(
        self,
        url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        verify_ssl: bool | None = None,
    ) -> JenkinsClient:
        """Create a Jenkins client with provided args or current settings.

        Args:
            url: Jenkins server URL (uses settings if not provided)
            username: Jenkins username (uses settings if not provided)
            password: Jenkins API token/password (uses settings if not provided)
            verify_ssl: Whether to verify SSL certificates (uses settings if not provided)

        Returns:
            Configured JenkinsClient instance

        Raises:
            ValueError: If Jenkins is not configured and no parameters provided
        """

        # Prefer provided args over config
        config = self.get_jenkins_config()

        final_url = url or config["url"]
        final_username = username or config["username"]
        final_password = password or config["password"]
        final_verify_ssl = verify_ssl if verify_ssl is not None else config["verify_ssl"]

        if not isinstance(final_url, str) or not isinstance(final_username, str) or not isinstance(final_password, str):
            raise ValueError("Jenkins configuration contains invalid types")

        if not isinstance(final_verify_ssl, bool):
            raise ValueError("Jenkins verify_ssl configuration must be boolean")

        return JenkinsClient(
            url=final_url, username=final_username, password=final_password, verify_ssl=final_verify_ssl
        )

    def create_configured_ai_client(self, api_key: str | None = None) -> AIAnalyzer:
        """Create an AI analyzer with provided args or current settings.

        Args:
            api_key: Gemini API key (uses settings if not provided)

        Returns:
            Configured AIAnalyzer instance

        Raises:
            ValueError: If AI service is not configured and no parameters provided
        """

        # Prefer provided args over config
        config = self.get_ai_config()

        final_api_key = api_key or config["api_key"]

        if not final_api_key:
            raise ValueError("AI service is not configured. Please provide an API key.")

        if not isinstance(final_api_key, str):
            raise ValueError("AI API key must be a string")

        gemini_client = GeminiClient(api_key=final_api_key)
        return AIAnalyzer(client=gemini_client)

    def create_configured_git_client(
        self, repo_url: str, branch: str | None = None, commit: str | None = None, github_token: str | None = None
    ) -> GitClient:
        """Create a Git client with provided args or current settings.

        Args:
            repo_url: Repository URL (required)
            branch: Branch name (optional)
            commit: Commit hash (optional)
            github_token: GitHub token (uses settings if not provided)

        Returns:
            Configured GitClient instance

        Raises:
            ValueError: If repo_url is not provided
            GitRepositoryError: If cloning fails
        """
        if not repo_url:
            raise ValueError("repo_url is required for GitClient")

        # Prefer provided args over config
        config = self.get_github_config()

        final_token = github_token or config["token"]

        return GitClient(repo_url=repo_url, branch=branch, commit=commit, github_token=final_token)

    def test_jenkins_connection(self, url: str, username: str, password: str, verify_ssl: bool = True) -> bool:
        """Test Jenkins connection with provided parameters.

        Args:
            url: Jenkins URL
            username: Jenkins username
            password: Jenkins API token/password
            verify_ssl: Whether to verify SSL certificates

        Returns:
            Response time in milliseconds

        Raises:
            ConnectionError: If Jenkins connection fails
            ValueError: If connection parameters are invalid
        """
        try:
            test_client = JenkinsClient(url=url, username=username, password=password, verify_ssl=verify_ssl)
            is_connected = test_client.is_connected()

            if is_connected:
                return True

            raise ConnectionError("Jenkins connection failed - Check URL, username, and API token")

        except Exception as e:
            if isinstance(e, ConnectionError):
                raise
            raise ConnectionError(f"Jenkins connection error: {str(e)}")

    def test_github_connection(self, token: str) -> bool:
        """Test GitHub connection with provided token.

        Args:
            token: GitHub personal access token

        Returns:
            Tuple of (username, response_time_ms)

        Raises:
            ConnectionError: If GitHub connection fails
            ValueError: If token is invalid
        """
        try:
            headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
            response = requests.get("https://api.github.com/user", headers=headers, timeout=10)

            if response.status_code == 200:
                return True
            else:
                raise ConnectionError(f"GitHub API error: {response.status_code} - {response.text}")

        except Exception as e:
            if isinstance(e, ConnectionError):
                raise
            raise ConnectionError(f"GitHub connection error: {str(e)}")

    def test_ai_connection(self, api_key: str) -> bool:
        """Test AI service connection with provided parameters.

        Args:
            api_key: Gemini API key
            model: Gemini model name
            temperature: AI temperature setting
            max_tokens: Maximum tokens for AI responses

        Returns:
            Tuple of (model_name, response_time_ms)

        Raises:
            ConnectionError: If AI service connection fails
            ValueError: If API key or model parameters are invalid
        """
        try:
            GeminiClient(api_key=api_key)
            return True

        except Exception as e:
            raise ConnectionError(f"AI service connection error: {str(e)}")

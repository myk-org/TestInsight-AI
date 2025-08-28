"""Service client creators for TestInsight AI."""

import re
from urllib.parse import urlparse

from backend.services.ai_analyzer import AIAnalyzer
from backend.services.gemini_api import GeminiClient
from backend.services.git_client import GitClient
from backend.services.jenkins_client import JenkinsClient
from backend.services.service_config.base import BaseServiceConfig
from backend.services.service_config.config_getters import ServiceConfigGetters


class ServiceClientCreators(BaseServiceConfig):
    """Service client creation methods."""

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
        getters = ServiceConfigGetters()
        config = getters.get_jenkins_config()

        final_url = url if url is not None else config.get("url")
        final_username = username if username is not None else config.get("username")
        final_password = password if password is not None else config.get("password")
        final_verify_ssl = verify_ssl if verify_ssl is not None else config.get("verify_ssl")

        if not isinstance(final_url, str) or not isinstance(final_username, str) or not isinstance(final_password, str):
            raise ValueError("Jenkins configuration contains invalid types")

        if not isinstance(final_verify_ssl, bool):
            raise ValueError("Jenkins verify_ssl configuration must be boolean")

        # Check if we have all required configuration values
        if not final_url or not final_username or not final_password:
            raise ValueError(
                "Jenkins is not configured. Please provide URL, username, and API token in settings or as parameters."
            )

        return JenkinsClient(
            url=final_url, username=final_username, password=final_password, verify_ssl=final_verify_ssl
        )

    def create_configured_ai_client(self, api_key: str | None = None) -> AIAnalyzer:
        """Create an AI analyzer with provided API key or current settings.

        Args:
            api_key: Gemini API key (uses settings if not provided)

        Returns:
            Configured AIAnalyzer instance

        Raises:
            ValueError: If AI service is not configured and no API key provided
        """
        # Prefer provided args over config
        getters = ServiceConfigGetters()
        config = getters.get_ai_config()

        final_api_key = api_key if api_key is not None else config.get("api_key")

        if not isinstance(final_api_key, str):
            raise TypeError("API key must be a string.")

        if not final_api_key or not final_api_key.strip():
            raise ValueError(
                "AI service is not configured. Please provide a Gemini API key in settings or as parameter."
            )

        # Compute defaults without falsy-coalescing pitfalls
        model = config.get("model")
        temperature = config.get("temperature")
        max_tokens = config.get("max_tokens")

        default_model = model if isinstance(model, str) and model else "gemini-2.5-pro"
        # Tolerate numeric strings from forms
        try:
            default_temperature = float(temperature) if temperature is not None else 0.7
        except (TypeError, ValueError):
            default_temperature = 0.7
        try:
            default_max_tokens = int(max_tokens) if max_tokens is not None else 4096
        except (TypeError, ValueError):
            default_max_tokens = 4096

        # Pass defaults via constructor so validation happens in the client
        gemini_client = GeminiClient(
            api_key=final_api_key,
            default_model=default_model,
            default_temperature=default_temperature,
            default_max_tokens=default_max_tokens,
        )
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
        if not repo_url or not str(repo_url).strip():
            raise ValueError("repo_url is required for GitClient")

        # Allow only https://, ssh:// or scp-like git URLs (user@host:path)
        repo_url = repo_url.strip()
        p = urlparse(repo_url)
        path_non_empty = bool(p.path and p.path.strip("/"))
        is_http_ssh = bool(p.scheme in ("https", "ssh") and p.netloc and path_non_empty)
        # Disallow whitespace anywhere and require non-empty path after colon
        is_scp_like = re.fullmatch(r"[^\s@]+@[^\s:]+:[^\s]+", repo_url) is not None
        if not (is_http_ssh or is_scp_like):
            raise ValueError("Invalid repository URL; only https://, ssh://, or scp-like formats allowed.")

        # Prefer provided args over config
        getters = ServiceConfigGetters()
        config = getters.get_github_config()

        final_token = github_token if github_token is not None else config.get("token")

        return GitClient(repo_url=repo_url, branch=branch, commit=commit, github_token=final_token)

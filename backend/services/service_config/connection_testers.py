"""Service connection testers for TestInsight AI."""

from typing import Any

import requests

from backend.services.service_config.base import BaseServiceConfig
from backend.services.service_config.client_creators import ServiceClientCreators
from backend.services.service_config.config_getters import ServiceConfigGetters


class ServiceConnectionTesters(BaseServiceConfig):
    """Service connection testing methods."""

    def test_jenkins_connection(
        self,
        url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        verify_ssl: bool | None = None,
    ) -> bool:
        """Test Jenkins connection with provided args or current settings.

        Args:
            url: Jenkins URL (uses settings if not provided)
            username: Jenkins username (uses settings if not provided)
            password: Jenkins API token/password (uses settings if not provided)
            verify_ssl: Whether to verify SSL certificates (uses settings if not provided)

        Returns:
            True if connection is successful

        Raises:
            ConnectionError: If Jenkins connection fails
            ValueError: If Jenkins is not configured and no parameters provided
        """
        try:
            # Use the create_configured method to follow the same pattern
            creators = ServiceClientCreators()
            client = creators.create_configured_jenkins_client(
                url=url, username=username, password=password, verify_ssl=verify_ssl
            )

            if not client.is_connected():
                raise ConnectionError("Jenkins connection failed")

            return True
        except ValueError as e:
            # Re-raise ValueError for proper error handling
            raise e
        except ConnectionError as e:
            # Re-raise ConnectionError for failed connections
            raise e
        except Exception as e:
            raise ConnectionError(f"Jenkins connection error: {str(e)}")

    def test_github_connection(self, token: str | None = None) -> bool:
        """Test GitHub connection with provided args or current settings.

        Args:
            token: GitHub personal access token (uses settings if not provided)

        Returns:
            True if connection is successful

        Raises:
            ConnectionError: If GitHub connection fails
            ValueError: If GitHub is not configured and no parameters provided
        """
        try:
            # Prefer provided args over config
            getters = ServiceConfigGetters()
            config = getters.get_github_config()
            final_token = token or config["token"]

            if not final_token:
                raise ValueError("GitHub is not configured. Please provide a token in settings or as parameter.")

            if not isinstance(final_token, str):
                raise ValueError("GitHub token must be a string")

            headers = {"Authorization": f"token {final_token}", "Accept": "application/vnd.github.v3+json"}
            response = requests.get("https://api.github.com/user", headers=headers, timeout=10)

            if response.status_code == 200:
                return True
            else:
                raise ConnectionError(f"GitHub API error: {response.status_code} - {response.text}")

        except ValueError as e:
            # Re-raise ValueError for proper error handling
            raise e
        except Exception as e:
            if isinstance(e, ConnectionError):
                raise
            raise ConnectionError(f"GitHub connection error: {str(e)}")

    def test_ai_connection(self) -> bool:
        """Test AI service connection using current settings and active authentication method.

        Returns:
            True if connection is successful

        Raises:
            ConnectionError: If AI service connection fails
            ValueError: If API key is not configured
        """
        try:
            # Use the create_configured method which will respect active_auth_method from settings
            creators = ServiceClientCreators()
            creators.create_configured_ai_client()
            return True
        except ValueError as e:
            # Re-raise ValueError for proper error handling
            raise e
        except Exception as e:
            raise ConnectionError(f"AI service connection error: {str(e)}")

    def test_ai_connection_with_config(self, ai_config: dict[str, Any]) -> bool:
        """Test AI service connection with provided configuration.

        Args:
            ai_config: AI configuration dictionary with API key

        Returns:
            True if connection is successful

        Raises:
            ConnectionError: If AI service connection fails
            ValueError: If configuration is invalid
        """
        try:
            # Extract API key from the test config
            api_key = ai_config.get("gemini_api_key")

            # Convert empty string to None for proper handling
            if api_key == "":
                api_key = None

            if not api_key or not api_key.strip():
                raise ValueError("AI service is not configured. Please provide a Gemini API key.")

            creators = ServiceClientCreators()
            creators.create_configured_ai_client(api_key=api_key)

            return True

        except ValueError as e:
            # Re-raise ValueError for proper error handling
            raise e
        except Exception as e:
            raise ConnectionError(f"AI service connection error: {str(e)}")

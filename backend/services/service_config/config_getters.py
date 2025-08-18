"""Service configuration getters for TestInsight AI."""

from backend.services.service_config.base import BaseServiceConfig


class ServiceConfigGetters(BaseServiceConfig):
    """Service configuration getters and status checkers."""

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

"""Service status checkers for TestInsight AI."""

from backend.services.service_config.config_getters import ServiceConfigGetters


class ServiceStatusCheckers(ServiceConfigGetters):
    """Service status checking methods."""

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

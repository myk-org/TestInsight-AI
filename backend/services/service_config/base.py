"""Base service configuration class for TestInsight AI."""

from backend.models.schemas import AppSettings
from backend.services.settings_service import SettingsService


class BaseServiceConfig:
    """Base service configuration with core functionality."""

    def __init__(self) -> None:
        """Initialize service configuration."""
        self._settings_service = SettingsService()

    def get_settings(self) -> AppSettings:
        """Get current settings (always fresh).

        Returns:
            Current application settings
        """
        return self._settings_service.get_settings()

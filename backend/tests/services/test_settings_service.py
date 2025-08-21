"""Tests for settings service."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from backend.services.settings_service import SettingsService
from backend.models.schemas import (
    AppSettings,
    SettingsUpdate,
    JenkinsSettings,
    AISettings,
)
from backend.tests.conftest import (
    FAKE_GEMINI_API_KEY,
    FAKE_GITHUB_TOKEN,
    FAKE_JENKINS_TOKEN,
    FAKE_NEW_API_KEY,
    FAKE_OLD_TOKEN,
    FAKE_USER1_TOKEN,
)


class TestSettingsService:
    """Test cases for SettingsService class."""

    def test_init_with_defaults(self):
        """Test SettingsService initialization with default settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"

            with patch("backend.services.settings_service.SettingsEncryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                assert service.settings_file == settings_file
                assert service.enable_encryption is False
                assert service._encryption is None
                assert settings_file.exists()

    def test_init_creates_directory(self):
        """Test SettingsService creates parent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "nested" / "dir" / "settings.json"

            with patch("backend.services.settings_service.SettingsEncryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                # Verify service created the directories and file
                assert service.settings_file.parent.exists()
                assert service.settings_file.exists()

    def test_init_with_encryption(self):
        """Test SettingsService initialization with encryption enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"
            mock_encryption = Mock()

            with patch("backend.services.settings_service.SettingsEncryption", return_value=mock_encryption):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=True)

                assert service.enable_encryption is True
                assert service._encryption == mock_encryption

    def test_get_settings_loads_from_file(self):
        """Test get_settings loads existing settings from file."""
        fake_settings_data = {
            "jenkins": {
                "url": "https://fake-jenkins.example.com",
                "username": "testuser",
                "api_token": FAKE_JENKINS_TOKEN,
                "verify_ssl": True,
            },
            "github": {"token": FAKE_GITHUB_TOKEN},
            "ai": {
                "gemini_api_key": FAKE_GEMINI_API_KEY,
                "model": "gemini-1.5-pro",
                "temperature": 0.8,
                "max_tokens": 2048,
            },
            "last_updated": "2024-01-01T12:00:00",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"
            settings_file.write_text(json.dumps(fake_settings_data))

            with patch("backend.services.settings_service.SettingsEncryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                settings = service.get_settings()

                assert isinstance(settings, AppSettings)
                assert settings.jenkins.url == "https://fake-jenkins.example.com"
                assert settings.github.token == FAKE_GITHUB_TOKEN
                assert settings.ai.gemini_api_key == FAKE_GEMINI_API_KEY

    def test_get_settings_caches_result(self):
        """Test get_settings caches the result."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"

            with patch("backend.services.settings_service.SettingsEncryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                # First call
                settings1 = service.get_settings()
                # Second call should return cached result
                settings2 = service.get_settings()

                assert settings1 is settings2  # Same object reference

    def test_get_settings_handles_corrupt_file(self):
        """Test get_settings handles corrupt JSON file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"
            settings_file.write_text("invalid json content")

            with patch("backend.services.settings_service.SettingsEncryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                settings = service.get_settings()

                # Should return default settings
                assert isinstance(settings, AppSettings)
                assert settings.jenkins.url is None
                assert settings.github.token is None

    def test_update_settings_jenkins_only(self):
        """Test update_settings with only Jenkins settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"

            with patch("backend.services.settings_service.SettingsEncryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                update = SettingsUpdate(
                    jenkins=JenkinsSettings(
                        url="https://new-jenkins.example.com",
                        username="newuser",
                        api_token="new_token_456",
                        verify_ssl=True,
                    ),
                    github=None,
                    ai=None,
                )

                result = service.update_settings(update)

                assert result.jenkins.url == "https://new-jenkins.example.com"
                assert result.jenkins.username == "newuser"
                assert result.jenkins.api_token == "new_token_456"
                # Other settings should remain default
                assert result.github.token is None
                assert result.ai.gemini_api_key is None

    def test_update_settings_multiple_sections(self):
        """Test update_settings with multiple sections."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"

            with patch("backend.services.settings_service.SettingsEncryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                update = SettingsUpdate(
                    jenkins=JenkinsSettings(
                        url="https://jenkins.example.com",
                        username="user1",
                        api_token=FAKE_USER1_TOKEN,
                        verify_ssl=True,
                    ),
                    ai=AISettings(
                        gemini_api_key=FAKE_NEW_API_KEY,
                        model="gemini-1.5-pro",
                        temperature=0.9,
                        max_tokens=4096,
                    ),
                    github=None,
                )

                result = service.update_settings(update)

                assert result.jenkins.url == "https://jenkins.example.com"
                assert result.ai.gemini_api_key == FAKE_NEW_API_KEY
                assert result.ai.model == "gemini-1.5-pro"

    def test_update_settings_merges_with_existing(self):
        """Test update_settings merges with existing settings."""
        fake_existing = {
            "jenkins": {
                "url": "https://old-jenkins.example.com",
                "username": "olduser",
                "api_token": FAKE_OLD_TOKEN,
                "verify_ssl": False,
            },
            "ai": {
                "gemini_api_key": "AIzaSyOldKey",
                "model": "gemini-1.0-pro",
                "temperature": 0.5,
                "max_tokens": 1024,
            },
            "last_updated": "2023-01-01T00:00:00",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"
            settings_file.write_text(json.dumps(fake_existing))

            with patch("backend.services.settings_service.SettingsEncryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                # Update only Jenkins URL - when updating a section, all fields in that section
                # are replaced with the new values. This is expected behavior.
                update = SettingsUpdate(
                    jenkins=JenkinsSettings(
                        url="https://new-jenkins.example.com",
                        username="olduser",  # Must provide to preserve
                        api_token=FAKE_OLD_TOKEN,  # Must provide to preserve
                        verify_ssl=False,  # Must provide to preserve
                    ),
                    github=None,
                    ai=None,
                )

                result = service.update_settings(update)

                assert result.jenkins.url == "https://new-jenkins.example.com"
                assert result.jenkins.username == "olduser"  # Preserved because explicitly provided
                assert result.jenkins.api_token == FAKE_OLD_TOKEN  # Preserved because explicitly provided
                assert result.jenkins.verify_ssl is False  # Preserved because explicitly provided
                # AI settings should remain unchanged
                assert result.ai.gemini_api_key == "AIzaSyOldKey"

    def test_reset_settings(self):
        """Test reset_settings creates default settings."""
        fake_existing = {
            "jenkins": {"url": "https://old.com", "username": "user", "api_token": FAKE_OLD_TOKEN, "verify_ssl": True},
            "github": {"token": FAKE_OLD_TOKEN},
            "ai": {
                "gemini_api_key": "old_key",
                "model": "old_model",
                "temperature": 0.5,
                "max_tokens": 1024,
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"
            settings_file.write_text(json.dumps(fake_existing))

            with patch("backend.services.settings_service.SettingsEncryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                result = service.reset_settings()

                # Should be default settings
                assert result.jenkins.url is None
                assert result.jenkins.username is None
                assert result.ai.gemini_api_key is None
                assert isinstance(result.last_updated, datetime)

"""Tests for settings service."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from backend.services.settings_service import SettingsService
from backend.models.schemas import (
    AppSettings,
    SettingsUpdate,
    JenkinsSettings,
    AISettings,
    UserPreferences,
)
from backend.services.security_utils import SettingsValidator


class TestSettingsService:
    """Test cases for SettingsService class."""

    def test_init_with_defaults(self):
        """Test SettingsService initialization with default settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"

            with patch("backend.services.settings_service.get_encryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                assert service.settings_file == settings_file
                assert service.enable_encryption is False
                assert service._encryption is None
                assert settings_file.exists()

    def test_init_creates_directory(self):
        """Test SettingsService creates parent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "nested" / "dir" / "settings.json"

            with patch("backend.services.settings_service.get_encryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                # Verify service created the directories and file
                assert service.settings_file.parent.exists()
                assert service.settings_file.exists()

    def test_init_with_encryption(self):
        """Test SettingsService initialization with encryption enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"
            mock_encryption = Mock()

            with patch("backend.services.settings_service.get_encryption", return_value=mock_encryption):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=True)

                assert service.enable_encryption is True
                assert service._encryption == mock_encryption

    def test_get_settings_loads_from_file(self):
        """Test get_settings loads existing settings from file."""
        fake_settings_data = {
            "jenkins": {
                "url": "https://fake-jenkins.example.com",
                "username": "testuser",
                "api_token": "fake_token_123",  # pragma: allowlist secret
                "verify_ssl": True,
            },
            "github": {"token": "fake_github_token_xyz"},  # pragma: allowlist secret
            "ai": {
                "gemini_api_key": "AIzaSyFakeKeyExample123456789",  # pragma: allowlist secret
                "model": "gemini-1.5-pro",
                "temperature": 0.8,
                "max_tokens": 2048,
            },
            "preferences": {"theme": "dark", "auto_analyze": True, "save_history": True},
            "last_updated": "2024-01-01T12:00:00",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"
            settings_file.write_text(json.dumps(fake_settings_data))

            with patch("backend.services.settings_service.get_encryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                settings = service.get_settings()

                assert isinstance(settings, AppSettings)
                assert settings.jenkins.url == "https://fake-jenkins.example.com"
                assert settings.github.token == "fake_github_token_xyz"  # pragma: allowlist secret
                assert settings.ai.gemini_api_key == "AIzaSyFakeKeyExample123456789"  # pragma: allowlist secret
                assert settings.preferences.theme == "dark"

    def test_get_settings_caches_result(self):
        """Test get_settings caches the result."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"

            with patch("backend.services.settings_service.get_encryption", return_value=None):
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

            with patch("backend.services.settings_service.get_encryption", return_value=None):
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

            with patch("backend.services.settings_service.get_encryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                update = SettingsUpdate(
                    jenkins=JenkinsSettings(
                        url="https://new-jenkins.example.com",
                        username="newuser",
                        api_token="new_token_456",  # pragma: allowlist secret
                    )
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

            with patch("backend.services.settings_service.get_encryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                update = SettingsUpdate(
                    jenkins=JenkinsSettings(
                        url="https://jenkins.example.com", username="user1", api_token="token1"
                    ),  # pragma: allowlist secret
                    ai=AISettings(
                        gemini_api_key="AIzaSyNewKey123",  # pragma: allowlist secret
                        gemini_model="gemini-1.5-pro",
                        temperature=0.9,  # pragma: allowlist secret
                    ),  # pragma: allowlist secret
                    preferences=UserPreferences(theme="light", auto_refresh=False),
                )

                result = service.update_settings(update)

                assert result.jenkins.url == "https://jenkins.example.com"
                assert result.ai.gemini_api_key == "AIzaSyNewKey123"  # pragma: allowlist secret
                assert result.ai.gemini_model == "gemini-1.5-pro"
                assert result.preferences.theme == "light"
                assert result.preferences.auto_refresh is False

    def test_update_settings_merges_with_existing(self):
        """Test update_settings merges with existing settings."""
        fake_existing = {
            "jenkins": {
                "url": "https://old-jenkins.example.com",
                "username": "olduser",
                "api_token": "old_token",  # pragma: allowlist secret
                "verify_ssl": False,
            },
            "ai": {
                "gemini_api_key": "AIzaSyOldKey",  # pragma: allowlist secret
                "model": "gemini-1.0-pro",
                "temperature": 0.5,
                "max_tokens": 1024,
            },  # pragma: allowlist secret
            "last_updated": "2023-01-01T00:00:00",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"
            settings_file.write_text(json.dumps(fake_existing))

            with patch("backend.services.settings_service.get_encryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                # Update only Jenkins URL - when updating a section, all fields in that section
                # are replaced with the new values. This is expected behavior.
                update = SettingsUpdate(
                    jenkins=JenkinsSettings(
                        url="https://new-jenkins.example.com",
                        username="olduser",  # Must provide to preserve
                        api_token="old_token",  # Must provide to preserve
                        verify_ssl=False,  # Must provide to preserve
                    )
                )

                result = service.update_settings(update)

                assert result.jenkins.url == "https://new-jenkins.example.com"
                assert result.jenkins.username == "olduser"  # Preserved because explicitly provided
                assert result.jenkins.api_token == "old_token"  # Preserved because explicitly provided
                assert result.jenkins.verify_ssl is False  # Preserved because explicitly provided
                # AI settings should remain unchanged
                assert result.ai.gemini_api_key == "AIzaSyOldKey"  # pragma: allowlist secret

    def test_reset_settings(self):
        """Test reset_settings creates default settings."""
        fake_existing = {
            "jenkins": {"url": "https://old.com", "username": "user"},
            "ai": {"gemini_api_key": "old_key"},  # pragma: allowlist secret
        }  # pragma: allowlist secret

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"
            settings_file.write_text(json.dumps(fake_existing))

            with patch("backend.services.settings_service.get_encryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                result = service.reset_settings()

                # Should be default settings
                assert result.jenkins.url is None
                assert result.jenkins.username is None
                assert result.ai.gemini_api_key is None
                assert isinstance(result.last_updated, datetime)

    def test_get_masked_settings(self):
        """Test get_masked_settings masks sensitive data."""
        fake_settings = {
            "jenkins": {
                "url": "https://jenkins.example.com",
                "username": "testuser",
                "api_token": "very_long_secret_token_12345",
            },
            "github": {"token": "ghp_short_token"},  # pragma: allowlist secret
            "ai": {"gemini_api_key": "AIzaSyVeryLongSecretKey123456789"},  # pragma: allowlist secret
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"
            settings_file.write_text(json.dumps(fake_settings))

            with patch("backend.services.settings_service.get_encryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                masked = service.get_masked_settings()

                # Long tokens should show first 4 and last 4 chars
                assert masked.jenkins.api_token == "very...2345"
                assert masked.ai.gemini_api_key == "AIza...6789"  # pragma: allowlist secret
                # Tokens longer than 8 chars show first 4 and last 4
                assert masked.github.token == "ghp_...oken"
                # Non-sensitive fields should remain unchanged
                assert masked.jenkins.username == "testuser"

    def test_get_masked_settings_empty_values(self):
        """Test get_masked_settings handles empty values."""
        fake_settings = {
            "jenkins": {
                "url": "https://jenkins.example.com",
                "username": "testuser",
                "api_token": "",  # Empty token
            },
            "github": {
                "token": None  # None token
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"
            settings_file.write_text(json.dumps(fake_settings, default=str))

            with patch("backend.services.settings_service.get_encryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                masked = service.get_masked_settings()

                # Empty/None values should remain unchanged
                assert masked.jenkins.api_token == ""
                assert masked.github.token is None

    def test_validate_settings_success(self):
        """Test validate_settings with valid settings."""
        fake_settings = {
            "jenkins": {"url": "https://jenkins.example.com", "username": "testuser", "api_token": "valid_token_123"},
            "github": {"token": "ghp_valid_github_token"},  # pragma: allowlist secret
            "ai": {
                "gemini_api_key": "AIzaSyValidKey123456789",  # pragma: allowlist secret
                "temperature": 0.7,
                "max_tokens": 4096,
            },  # pragma: allowlist secret
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"
            settings_file.write_text(json.dumps(fake_settings))

            with (
                patch("backend.services.security_utils.get_encryption", return_value=None),
                patch.object(SettingsValidator, "validate_jenkins_url", return_value=[]),
                patch.object(SettingsValidator, "validate_github_token", return_value=[]),
                patch.object(SettingsValidator, "validate_gemini_api_key", return_value=[]),
            ):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                errors = service.validate_settings()

                assert errors == {}  # No validation errors

    def test_validate_settings_jenkins_errors(self):
        """Test validate_settings with Jenkins validation errors."""
        fake_settings = {
            "jenkins": {
                "url": "invalid-url",
                "username": "",  # Missing username
                "api_token": "",  # Missing token
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"
            settings_file.write_text(json.dumps(fake_settings))

            with (
                patch("backend.services.security_utils.get_encryption", return_value=None),
                patch.object(SettingsValidator, "validate_jenkins_url", return_value=["Invalid URL format"]),
            ):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                errors = service.validate_settings()

                assert "jenkins" in errors
                jenkins_errors = errors["jenkins"]
                assert "Invalid URL format" in jenkins_errors
                assert "Jenkins username is required when URL is provided" in jenkins_errors
                assert "Jenkins API token is required when URL is provided" in jenkins_errors

    def test_validate_settings_ai_parameter_errors(self):
        """Test validate_settings with AI parameter validation errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"

            with (
                patch("backend.services.settings_service.get_encryption", return_value=None),
                patch.object(SettingsValidator, "validate_gemini_api_key", return_value=[]),
            ):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                # Get valid settings and manually modify them to bypass schema validation
                settings = service.get_settings()
                # Use object.__setattr__ to bypass pydantic validation
                object.__setattr__(settings.ai, "temperature", 3.0)  # Invalid - too high
                object.__setattr__(settings.ai, "max_tokens", 100000)  # Invalid - too high

                # Manually set the current settings to our modified ones
                service._current_settings = settings

                errors = service.validate_settings()

                assert "ai" in errors
                ai_errors = errors["ai"]
                assert "Temperature must be between 0.0 and 2.0" in ai_errors
                assert "Max tokens must be between 1 and 32768" in ai_errors

    def test_encrypt_sensitive_fields(self):
        """Test _encrypt_sensitive_fields encrypts sensitive data."""
        mock_encryption = Mock()
        mock_encryption.encrypt.side_effect = lambda x: f"encrypted_{x}"

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"

            with patch("backend.services.settings_service.get_encryption", return_value=mock_encryption):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=True)

                settings_dict = {
                    "jenkins": {
                        "url": "https://jenkins.example.com",
                        "username": "testuser",
                        "api_token": "secret_token",
                    },
                    "github": {"token": "github_token"},  # pragma: allowlist secret
                    "ai": {"gemini_api_key": "api_key"},  # pragma: allowlist secret
                }

                result = service._encrypt_sensitive_fields(settings_dict)

                assert result["jenkins"]["api_token"] == "encrypted_secret_token"
                assert result["github"]["token"] == "encrypted_github_token"  # pragma: allowlist secret
                assert result["ai"]["gemini_api_key"] == "encrypted_api_key"  # pragma: allowlist secret
                # Non-sensitive fields unchanged
                assert result["jenkins"]["username"] == "testuser"

    def test_encrypt_sensitive_fields_disabled(self):
        """Test _encrypt_sensitive_fields when encryption disabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"

            with patch("backend.services.settings_service.get_encryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                settings_dict = {"jenkins": {"api_token": "secret_token"}}

                result = service._encrypt_sensitive_fields(settings_dict)

                # Should be unchanged when encryption disabled
                assert result == settings_dict

    def test_decrypt_sensitive_fields(self):
        """Test _decrypt_sensitive_fields decrypts encrypted data."""
        mock_encryption = Mock()
        mock_encryption.is_encrypted.return_value = True
        mock_encryption.decrypt.side_effect = lambda x: x.replace("encrypted_", "")

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"

            with patch("backend.services.settings_service.get_encryption", return_value=mock_encryption):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=True)

                settings_dict = {
                    "jenkins": {"api_token": "encrypted_secret_token"},  # pragma: allowlist secret
                    "github": {"token": "encrypted_github_token"},  # pragma: allowlist secret
                    "ai": {"gemini_api_key": "encrypted_api_key"},  # pragma: allowlist secret
                }

                result = service._decrypt_sensitive_fields(settings_dict)

                assert result["jenkins"]["api_token"] == "secret_token"
                assert result["github"]["token"] == "github_token"
                assert result["ai"]["gemini_api_key"] == "api_key"  # pragma: allowlist secret

    def test_decrypt_sensitive_fields_unencrypted_data(self):
        """Test _decrypt_sensitive_fields handles unencrypted legacy data."""
        mock_encryption = Mock()
        mock_encryption.is_encrypted.return_value = False  # Not encrypted

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"

            with patch("backend.services.settings_service.get_encryption", return_value=mock_encryption):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=True)

                settings_dict = {"jenkins": {"api_token": "plain_token"}}

                result = service._decrypt_sensitive_fields(settings_dict)

                # Should remain unchanged for unencrypted data
                assert result["jenkins"]["api_token"] == "plain_token"

    def test_backup_settings(self):
        """Test backup_settings creates backup file."""
        fake_settings = {"jenkins": {"url": "https://jenkins.example.com"}, "last_updated": "2024-01-01T12:00:00"}

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"
            settings_file.write_text(json.dumps(fake_settings))

            with patch("backend.services.settings_service.get_encryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                backup_path = service.backup_settings()

                assert Path(backup_path).exists()
                assert "settings_backup_" in backup_path

                # Verify backup content
                with open(backup_path, "r") as f:
                    backup_data = json.load(f)
                assert backup_data["jenkins"]["url"] == "https://jenkins.example.com"

    def test_backup_settings_custom_path(self):
        """Test backup_settings with custom backup path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"
            custom_backup = Path(temp_dir) / "custom_backup.json"

            with patch("backend.services.settings_service.get_encryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                result_path = service.backup_settings(str(custom_backup))

                assert result_path == str(custom_backup)
                assert custom_backup.exists()

    def test_restore_settings(self):
        """Test restore_settings from backup file."""
        backup_data = {
            "jenkins": {"url": "https://restored-jenkins.example.com", "username": "restored_user"},
            "ai": {"gemini_api_key": "restored_key"},  # pragma: allowlist secret
            "last_updated": "2023-12-01T10:00:00",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"
            backup_file = Path(temp_dir) / "backup.json"
            backup_file.write_text(json.dumps(backup_data))

            with patch("backend.services.settings_service.get_encryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                result = service.restore_settings(str(backup_file))

                assert result.jenkins.url == "https://restored-jenkins.example.com"
                assert result.jenkins.username == "restored_user"
                assert result.ai.gemini_api_key == "restored_key"  # pragma: allowlist secret

                # Verify settings were saved to file
                current_settings = service.get_settings()
                assert current_settings.jenkins.url == "https://restored-jenkins.example.com"

    def test_restore_settings_file_not_found(self):
        """Test restore_settings with missing backup file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"

            with patch("backend.services.settings_service.get_encryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                with pytest.raises(FileNotFoundError, match="Backup file not found"):
                    service.restore_settings("nonexistent_backup.json")

    def test_restore_settings_invalid_backup(self):
        """Test restore_settings with invalid backup file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"
            backup_file = Path(temp_dir) / "invalid_backup.json"
            backup_file.write_text("invalid json content")

            with patch("backend.services.settings_service.get_encryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                with pytest.raises(ValueError, match="Invalid backup file"):
                    service.restore_settings(str(backup_file))

    def test_save_settings_handles_datetime(self):
        """Test _save_settings properly handles datetime serialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"

            with patch("backend.services.settings_service.get_encryption", return_value=None):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

                settings = AppSettings(last_updated=datetime.now())
                service._save_settings(settings)

                # Should be able to load back without errors
                loaded_settings = service._load_settings()
                assert isinstance(loaded_settings.last_updated, datetime)

    def test_encryption_error_handling(self):
        """Test encryption error handling doesn't break the service."""
        mock_encryption = Mock()
        mock_encryption.encrypt.side_effect = Exception("Encryption failed")

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"

            with (
                patch("backend.services.settings_service.get_encryption", return_value=mock_encryption),
                patch("builtins.print") as mock_print,
            ):  # Capture print statements
                service = SettingsService(settings_file=str(settings_file), enable_encryption=True)

                settings = AppSettings()
                settings.jenkins.api_token = "test_token"

                # Should not raise exception, but print warning
                service._save_settings(settings)

                # Verify warning was printed
                mock_print.assert_called()
                warning_call = str(mock_print.call_args_list[0])
                assert "Warning: Failed to encrypt" in warning_call

    def test_decryption_error_handling(self):
        """Test decryption error handling for legacy data."""
        mock_encryption = Mock()
        mock_encryption.is_encrypted.return_value = True
        mock_encryption.decrypt.side_effect = Exception("Decryption failed")

        settings_data = {"jenkins": {"api_token": "encrypted_but_corrupted_token"}}

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"
            settings_file.write_text(json.dumps(settings_data))

            with (
                patch("backend.services.settings_service.get_encryption", return_value=mock_encryption),
                patch("builtins.print") as mock_print,
            ):
                service = SettingsService(settings_file=str(settings_file), enable_encryption=True)

                # Should load without crashing
                settings = service._load_settings()

                # Verify settings were loaded (even with decryption errors)
                assert settings is not None

                # Warning should be printed
                mock_print.assert_called()
                warning_call = str(mock_print.call_args_list[0])
                assert "Warning: Failed to decrypt" in warning_call

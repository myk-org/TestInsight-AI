"""Tests for settings service coverage."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from backend.services.settings_service import SettingsService
from backend.models.schemas import AppSettings, JenkinsSettings, GitHubSettings, AISettings


def test_get_secret_status():
    """Test get_secret_status method."""
    with tempfile.TemporaryDirectory() as temp_dir:
        settings_file = Path(temp_dir) / "settings.json"
        service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

        settings = AppSettings(
            jenkins=JenkinsSettings(api_token="fake_token"),
            github=GitHubSettings(token="fake_token"),
            ai=AISettings(gemini_api_key="fake_key"),
            last_updated=datetime.now(),
        )
        service._save_settings(settings)
        service._current_settings = settings

        status = service.get_secret_status()
        assert status["jenkins"]["api_token"] is True
        assert status["github"]["token"] is True
        assert status["ai"]["gemini_api_key"] is True


def test_encrypt_decrypt_sensitive_fields():
    """Test encryption and decryption of sensitive fields."""
    with tempfile.TemporaryDirectory() as temp_dir:
        settings_file = Path(temp_dir) / "settings.json"
        service = SettingsService(settings_file=str(settings_file), enable_encryption=True)

        settings_dict = {
            "jenkins": {"api_token": "secret"},
            "github": {"token": "secret"},
            "ai": {"gemini_api_key": "secret"},
        }

        encrypted = service._encrypt_sensitive_fields(settings_dict)
        assert encrypted["jenkins"]["api_token"] != "secret"

        decrypted = service._decrypt_sensitive_fields(encrypted)
        assert decrypted["jenkins"]["api_token"] == "secret"


def test_backup_and_restore_settings():
    """Test backup and restore settings."""
    with tempfile.TemporaryDirectory() as temp_dir:
        settings_file = Path(temp_dir) / "settings.json"
        service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

        settings = AppSettings(
            jenkins=JenkinsSettings(url="http://test.com"),
            github=GitHubSettings(token="test_token"),
            ai=AISettings(gemini_api_key="test_key"),
            last_updated=datetime.now(),
        )
        service._save_settings(settings)
        service._current_settings = settings

        backup_path = service.backup_settings()
        restored_settings = service.restore_settings(backup_path)

        assert restored_settings.jenkins.url == "http://test.com"
        assert restored_settings.github.token == "test_token"
        assert restored_settings.ai.gemini_api_key == "test_key"


def test_get_masked_settings(client):
    """Test get_masked_settings method."""
    with tempfile.TemporaryDirectory() as temp_dir:
        settings_file = Path(temp_dir) / "settings.json"
        service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

        settings = AppSettings(
            jenkins=JenkinsSettings(api_token="fake_token_long_enough"),
            github=GitHubSettings(token="short"),
            ai=AISettings(gemini_api_key=""),
            last_updated=datetime.now(),
        )
        service._save_settings(settings)
        service._current_settings = settings

        masked_settings = service.get_masked_settings()
        assert masked_settings.jenkins.api_token == "fake...ough"
        assert masked_settings.github.token == "***masked***"
        assert masked_settings.ai.gemini_api_key == ""


def test_validate_settings(client):
    """Test validate_settings method."""
    with tempfile.TemporaryDirectory() as temp_dir:
        settings_file = Path(temp_dir) / "settings.json"
        service = SettingsService(settings_file=str(settings_file), enable_encryption=False)

        settings = AppSettings(
            jenkins=JenkinsSettings(url="invalid-url"),
            github=GitHubSettings(token="short"),
            ai=AISettings(gemini_api_key="invalid-key", temperature=0.7, max_tokens=4096),
            last_updated=datetime.now(),
        )
        settings.ai.temperature = 3.0
        settings.ai.max_tokens = 99999
        service._save_settings(settings)
        service._current_settings = settings

        errors = service.validate_settings()
        assert "jenkins" in errors
        assert "github" in errors
        assert "ai" in errors


def test_restore_settings_file_not_found(client):
    """Test restore_settings with a file that does not exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        settings_file = Path(temp_dir) / "settings.json"
        service = SettingsService(settings_file=str(settings_file), enable_encryption=False)
        with pytest.raises(FileNotFoundError):
            service.restore_settings("nonexistent_backup.json")


def test_restore_settings_invalid_json(client):
    """Test restore_settings with an invalid JSON file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        settings_file = Path(temp_dir) / "settings.json"
        service = SettingsService(settings_file=str(settings_file), enable_encryption=False)
        backup_path = Path(temp_dir) / "invalid.json"
        backup_path.write_text("invalid json")
        with pytest.raises(ValueError):
            service.restore_settings(str(backup_path))

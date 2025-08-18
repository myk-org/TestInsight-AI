"""Settings management service for TestInsight AI."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.models.schemas import AppSettings, SettingsUpdate
from backend.services.security_utils import SettingsEncryption, SettingsValidator


class SettingsService:
    """Service for managing application settings with secure storage."""

    def __init__(self, settings_file: str = "data/settings.json", enable_encryption: bool = True):
        """Initialize settings service.

        Args:
            settings_file: Path to settings file. Defaults to data/settings.json
            enable_encryption: Whether to encrypt sensitive data
        """
        # Create data directory if it doesn't exist
        settings_path = Path(settings_file)
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        self.settings_file = Path(settings_path)
        self._current_settings: AppSettings | None = None
        self.enable_encryption = enable_encryption
        self._encryption = SettingsEncryption() if enable_encryption else None

        # Ensure the settings file exists with default values
        if not self.settings_file.exists():
            self._save_settings(AppSettings(last_updated=datetime.now()))

    def get_settings(self) -> AppSettings:
        """Get current application settings.

        Returns:
            Current application settings
        """
        if self._current_settings is None:
            self._current_settings = self._load_settings()

        return self._current_settings

    def update_settings(self, update: SettingsUpdate) -> AppSettings:
        """Update application settings.

        Args:
            update: Settings update request

        Returns:
            Updated settings
        """
        current = self.get_settings()

        # Update only provided sections
        update_data = {}

        if update.jenkins is not None:
            update_data["jenkins"] = update.jenkins.model_dump()

        if update.github is not None:
            update_data["github"] = update.github.model_dump()

        if update.ai is not None:
            update_data["ai"] = update.ai.model_dump()

        if update.preferences is not None:
            update_data["preferences"] = update.preferences.model_dump()

        # Add timestamp
        update_data["last_updated"] = datetime.now()

        # Merge with current settings, preserving existing secrets when empty values are sent
        current_dict = current.model_dump()

        # Define which fields are secrets that should be preserved when empty
        secret_fields = {"jenkins": ["api_token"], "github": ["token"], "ai": ["gemini_api_key"]}

        for section, data in update_data.items():
            if section in current_dict:
                if isinstance(current_dict[section], dict) and isinstance(data, dict):
                    # For secret fields, only update if new value is provided and not empty
                    for field, value in data.items():
                        if (
                            section in secret_fields
                            and field in secret_fields[section]
                            and (not value or not str(value).strip())
                        ):
                            # Keep existing secret value if new value is empty
                            continue
                        current_dict[section][field] = value
                else:
                    current_dict[section] = data
            else:
                current_dict[section] = data

        # Create new settings object
        updated_settings = AppSettings(**current_dict)

        # Save and cache
        self._save_settings(updated_settings)
        self._current_settings = updated_settings

        return updated_settings

    def reset_settings(self) -> AppSettings:
        """Reset settings to defaults.

        Returns:
            Default settings
        """
        default_settings = AppSettings(last_updated=datetime.now())
        self._save_settings(default_settings)
        self._current_settings = default_settings
        return default_settings

    def get_masked_settings(self) -> AppSettings:
        """Get settings with sensitive data masked.

        Returns:
            Settings with sensitive values masked
        """
        settings = self.get_settings()
        settings_dict = settings.model_dump()

        # Clear sensitive fields but preserve other data
        sensitive_fields = [
            ("jenkins", "api_token"),
            ("github", "token"),
            ("ai", "gemini_api_key"),
        ]

        for section, field in sensitive_fields:
            if section in settings_dict and field in settings_dict[section]:
                value = settings_dict[section][field]
                if value and len(str(value)) > 8:
                    # Mask long values: show first 4 and last 4 chars
                    masked_value = f"{str(value)[:4]}...{str(value)[-4:]}"
                    settings_dict[section][field] = masked_value
                elif value:
                    # For shorter values, mask completely
                    settings_dict[section][field] = "***masked***"
                else:
                    # Keep empty/None values as-is
                    settings_dict[section][field] = value

        return AppSettings(**settings_dict)

    def get_secret_status(self) -> dict[str, dict[str, bool]]:
        """Get status of whether secrets are configured.

        Returns:
            Dictionary indicating which secrets are set
        """
        settings = self.get_settings()

        return {
            "jenkins": {"api_token": bool(settings.jenkins.api_token and settings.jenkins.api_token.strip())},
            "github": {"token": bool(settings.github.token and settings.github.token.strip())},
            "ai": {"gemini_api_key": bool(settings.ai.gemini_api_key and settings.ai.gemini_api_key.strip())},
        }

    def validate_settings(self) -> dict[str, list[str]]:
        """Validate current settings and return any issues.

        Returns:
            Dictionary with validation errors by section
        """
        settings = self.get_settings()
        errors = {}

        # Validate Jenkins settings using security validator
        jenkins_errors = []
        if settings.jenkins.url:
            jenkins_errors.extend(SettingsValidator.validate_jenkins_url(settings.jenkins.url))

            if not settings.jenkins.username:
                jenkins_errors.append("Jenkins username is required when URL is provided")

            if not settings.jenkins.api_token:
                jenkins_errors.append("Jenkins API token is required when URL is provided")

        if jenkins_errors:
            errors["jenkins"] = jenkins_errors

        # Validate GitHub settings
        github_errors = []
        if settings.github.token:
            github_errors.extend(SettingsValidator.validate_github_token(settings.github.token))

        if github_errors:
            errors["github"] = github_errors

        # Validate AI settings
        ai_errors = []
        if settings.ai.gemini_api_key:
            ai_errors.extend(SettingsValidator.validate_gemini_api_key(settings.ai.gemini_api_key))

        if settings.ai.temperature < 0.0 or settings.ai.temperature > 2.0:
            ai_errors.append("Temperature must be between 0.0 and 2.0")

        if settings.ai.max_tokens < 1 or settings.ai.max_tokens > 32768:
            ai_errors.append("Max tokens must be between 1 and 32768")

        if ai_errors:
            errors["ai"] = ai_errors

        return errors

    def _encrypt_sensitive_fields(self, settings_dict: dict[str, Any]) -> dict[str, Any]:
        """Encrypt sensitive fields in settings dictionary.

        Args:
            settings_dict: Settings dictionary to encrypt

        Returns:
            Dictionary with encrypted sensitive fields
        """
        if not self.enable_encryption or not self._encryption:
            return settings_dict

        # Make a copy to avoid modifying the original
        encrypted_dict = json.loads(json.dumps(settings_dict, default=str))

        # Define sensitive fields to encrypt
        sensitive_fields = [
            ("jenkins", "api_token"),
            ("github", "token"),
            ("ai", "gemini_api_key"),
        ]

        for section, field in sensitive_fields:
            if section in encrypted_dict and field in encrypted_dict[section] and encrypted_dict[section][field]:
                try:
                    encrypted_dict[section][field] = self._encryption.encrypt(encrypted_dict[section][field])
                except Exception as e:
                    # Log error but don't fail completely
                    print(f"Warning: Failed to encrypt {section}.{field}: {e}")

        return encrypted_dict

    def _decrypt_sensitive_fields(self, settings_dict: dict[str, Any]) -> dict[str, Any]:
        """Decrypt sensitive fields in settings dictionary.

        Args:
            settings_dict: Settings dictionary with encrypted fields

        Returns:
            Dictionary with decrypted sensitive fields
        """
        if not self.enable_encryption or not self._encryption:
            return settings_dict

        # Make a copy to avoid modifying the original
        decrypted_dict = json.loads(json.dumps(settings_dict, default=str))

        # Define sensitive fields to decrypt
        sensitive_fields = [
            ("jenkins", "api_token"),
            ("github", "token"),
            ("ai", "gemini_api_key"),
        ]

        for section, field in sensitive_fields:
            if section in decrypted_dict and field in decrypted_dict[section] and decrypted_dict[section][field]:
                try:
                    # Only decrypt if it looks encrypted
                    value = decrypted_dict[section][field]
                    if self._encryption.is_encrypted(value):
                        decrypted_dict[section][field] = self._encryption.decrypt(value)
                except Exception as e:
                    # Log error but don't fail completely - might be unencrypted legacy data
                    print(f"Warning: Failed to decrypt {section}.{field}: {e}")

        return decrypted_dict

    def _load_settings(self) -> AppSettings:
        """Load settings from file."""
        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Decrypt sensitive fields before creating settings object
            decrypted_data = self._decrypt_sensitive_fields(data)
            return AppSettings(**decrypted_data)
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            # Create default settings if file doesn't exist or is invalid
            _current_settings = AppSettings(last_updated=datetime.now())
            self._save_settings(_current_settings)
            return _current_settings

    def _save_settings(self, settings: AppSettings) -> None:
        """Save settings to file.

        Args:
            settings: Settings to save
        """
        # Ensure parent directory exists
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)

        # Get settings as dictionary
        settings_dict = settings.model_dump(mode="json")

        # Encrypt sensitive fields before saving
        encrypted_dict = self._encrypt_sensitive_fields(settings_dict)

        # Save with proper formatting
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(
                encrypted_dict,
                f,
                indent=2,
                ensure_ascii=False,
                default=str,  # Handle datetime serialization
            )

    def backup_settings(self, backup_path: str | None = None) -> str:
        """Create a backup of current settings.

        Args:
            backup_path: Path for backup file. Auto-generated if None.

        Returns:
            Path to backup file
        """
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"data/settings_backup_{timestamp}.json"

        backup_file = Path(backup_path)
        backup_file.parent.mkdir(parents=True, exist_ok=True)

        settings = self.get_settings()
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(settings.model_dump(mode="json"), f, indent=2, ensure_ascii=False, default=str)

        return str(backup_file)

    def restore_settings(self, backup_path: str) -> AppSettings:
        """Restore settings from backup.

        Args:
            backup_path: Path to backup file

        Returns:
            Restored settings

        Raises:
            FileNotFoundError: If backup file doesn't exist
            ValueError: If backup file is invalid
        """
        backup_file = Path(backup_path)
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        try:
            with open(backup_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            restored_settings = AppSettings(**data)
            self._save_settings(restored_settings)
            self._current_settings = restored_settings

            return restored_settings
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Invalid backup file: {e}")

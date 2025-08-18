"""Tests for security utilities."""

from unittest.mock import Mock, patch

import pytest

from backend.services.security_utils import (
    InputSanitizer,
    SettingsEncryption,
    SettingsValidator,
    generate_encryption_key,
    get_encryption,
    secure_compare,
)
from backend.tests.conftest import (
    FAKE_DEFAULT_PASSWORD,
    FAKE_ENV_PASSWORD,
    FAKE_PADDED_TOKEN,
    FAKE_SENSITIVE_TOKEN,
    FAKE_SHORT_TOKEN,
    FAKE_TEST_PASSWORD,
)


class TestInputSanitizer:
    """Test InputSanitizer class."""

    def test_sanitize_url_valid(self):
        """Test sanitizing valid URLs."""
        sanitizer = InputSanitizer()

        # Test valid HTTPS URL
        url = "https://fake-jenkins.example.com"
        result = sanitizer.sanitize_url(url)
        assert result == url

        # Test valid HTTP URL
        url = "http://fake-server.local"
        result = sanitizer.sanitize_url(url)
        assert result == url

    def test_sanitize_url_empty(self):
        """Test sanitizing empty URL."""
        sanitizer = InputSanitizer()
        assert sanitizer.sanitize_url("") == ""
        assert sanitizer.sanitize_url(None) is None

    def test_sanitize_url_strips_whitespace(self):
        """Test URL sanitization strips whitespace."""
        sanitizer = InputSanitizer()
        url = "  https://fake-jenkins.example.com  "
        result = sanitizer.sanitize_url(url)
        assert result == "https://fake-jenkins.example.com"

    def test_sanitize_url_dangerous_content(self):
        """Test URL sanitization rejects dangerous content."""
        sanitizer = InputSanitizer()

        dangerous_urls = [
            "javascript:alert('test')",
            "https://example.com<script>alert('xss')</script>",
            "https://example.com?onclick=alert('xss')",
            "https://example.com?onerror=alert('xss')",
        ]

        for url in dangerous_urls:
            with pytest.raises(ValueError, match="potentially dangerous content"):
                sanitizer.sanitize_url(url)

    def test_sanitize_token_valid(self):
        """Test sanitizing valid tokens."""
        sanitizer = InputSanitizer()

        token = FAKE_SHORT_TOKEN
        result = sanitizer.sanitize_token(token)
        assert result == token

    def test_sanitize_token_empty(self):
        """Test sanitizing empty token."""
        sanitizer = InputSanitizer()
        assert sanitizer.sanitize_token("") == ""
        assert sanitizer.sanitize_token(None) is None

    def test_sanitize_token_strips_whitespace(self):
        """Test token sanitization strips whitespace."""
        sanitizer = InputSanitizer()
        token = FAKE_PADDED_TOKEN
        result = sanitizer.sanitize_token(token)
        assert result == "fake_token_123"  # pragma: allowlist secret

    def test_sanitize_token_invalid_characters(self):
        """Test token sanitization rejects invalid characters."""
        sanitizer = InputSanitizer()

        invalid_tokens = ["token<script>", "token>alert", 'token"test', "token'test", "token&test"]

        for token in invalid_tokens:
            with pytest.raises(ValueError, match="invalid characters"):
                sanitizer.sanitize_token(token)

    def test_sanitize_username_valid(self):
        """Test sanitizing valid usernames."""
        sanitizer = InputSanitizer()

        username = "testuser123"
        result = sanitizer.sanitize_username(username)
        assert result == username

    def test_sanitize_username_empty(self):
        """Test sanitizing empty username."""
        sanitizer = InputSanitizer()
        assert sanitizer.sanitize_username("") == ""
        assert sanitizer.sanitize_username(None) is None

    def test_sanitize_username_strips_whitespace(self):
        """Test username sanitization strips whitespace."""
        sanitizer = InputSanitizer()
        username = "  testuser  "
        result = sanitizer.sanitize_username(username)
        assert result == "testuser"

    def test_sanitize_username_invalid_characters(self):
        """Test username sanitization rejects invalid characters."""
        sanitizer = InputSanitizer()

        invalid_usernames = [
            "user<script>",
            "user>test",
            'user"test',
            "user'test",
            "user&test",
            "user;test",
            "user|test",
        ]

        for username in invalid_usernames:
            with pytest.raises(ValueError, match="invalid characters"):
                sanitizer.sanitize_username(username)


class TestSettingsValidator:
    """Test SettingsValidator class."""

    def test_validate_jenkins_url_valid(self):
        """Test validating valid Jenkins URLs."""
        validator = SettingsValidator()

        # Valid HTTPS URL
        errors = validator.validate_jenkins_url("https://fake-jenkins.example.com")
        assert errors == []

        # Valid HTTP URL (with warning)
        errors = validator.validate_jenkins_url("http://fake-jenkins.example.com")
        assert len(errors) == 1
        assert "not secure" in errors[0]

    def test_validate_jenkins_url_empty(self):
        """Test validating empty Jenkins URL."""
        validator = SettingsValidator()
        errors = validator.validate_jenkins_url("")
        assert errors == []

    def test_validate_jenkins_url_invalid_protocol(self):
        """Test validating Jenkins URL with invalid protocol."""
        validator = SettingsValidator()
        errors = validator.validate_jenkins_url("ftp://fake-jenkins.example.com")
        assert len(errors) == 1
        assert "must start with http://" in errors[0]

    def test_validate_jenkins_url_dangerous_content(self):
        """Test validating Jenkins URL with dangerous content."""
        validator = SettingsValidator()
        errors = validator.validate_jenkins_url("https://example.com<script>")
        assert len(errors) == 1
        assert "dangerous content" in errors[0]

    def test_validate_github_token_valid(self):
        """Test validating valid GitHub tokens."""
        validator = SettingsValidator()

        # Valid GitHub token formats
        valid_tokens = [
            "ghp_fake1234567890123456789012345678",
            "github_pat_fake123456789012345678901234567890123456789012345678901234567890123456789",
            "gho_fake1234567890123456789012345678",
            "ghs_fake1234567890123456789012345678",
        ]

        for token in valid_tokens:
            errors = validator.validate_github_token(token)
            assert errors == []

    def test_validate_github_token_empty(self):
        """Test validating empty GitHub token."""
        validator = SettingsValidator()
        errors = validator.validate_github_token("")
        assert errors == []

    def test_validate_github_token_too_short(self):
        """Test validating GitHub token that's too short."""
        validator = SettingsValidator()
        errors = validator.validate_github_token("short")
        assert len(errors) == 1
        assert "too short" in errors[0]

    @patch("backend.services.security_utils.get_encryption")
    def test_validate_github_token_encrypted(self, mock_get_encryption):
        """Test validating encrypted GitHub token."""
        mock_encryption = Mock()
        mock_encryption.is_encrypted.return_value = True
        mock_get_encryption.return_value = mock_encryption

        validator = SettingsValidator()
        errors = validator.validate_github_token("encrypted_token_data")
        assert errors == []

    def test_validate_gemini_api_key_valid(self):
        """Test validating valid Gemini API key."""
        validator = SettingsValidator()

        # Valid Gemini API key format (39 characters total)
        api_key = "AIzaSyFakeKeyExample1234567890123456789"  # pragma: allowlist secret
        errors = validator.validate_gemini_api_key(api_key)
        assert errors == []

    def test_validate_gemini_api_key_empty(self):
        """Test validating empty Gemini API key."""
        validator = SettingsValidator()
        errors = validator.validate_gemini_api_key("")
        assert errors == []

    def test_validate_gemini_api_key_wrong_prefix(self):
        """Test validating Gemini API key with wrong prefix."""
        validator = SettingsValidator()
        errors = validator.validate_gemini_api_key("WrongPrefixExample123456789012345678901")
        assert len(errors) == 1
        assert "should start with 'AIzaSy'" in errors[0]

    def test_validate_gemini_api_key_wrong_length(self):
        """Test validating Gemini API key with wrong length."""
        validator = SettingsValidator()

        # Too short
        errors = validator.validate_gemini_api_key("AIzaSyShort")
        assert len(errors) == 1
        assert "39 characters long" in errors[0]

        # Too long
        errors = validator.validate_gemini_api_key(
            "AIzaSyTooLongExample1234567890123456789012345678901234567890"
        )  # pragma: allowlist secret
        assert len(errors) == 1
        assert "39 characters long" in errors[0]


class TestSettingsEncryption:
    """Test SettingsEncryption class."""

    def test_init_with_password(self):
        """Test initializing encryption with password."""
        encryption = SettingsEncryption(password=FAKE_TEST_PASSWORD)
        assert encryption.password == FAKE_TEST_PASSWORD

    @patch.dict("os.environ", {"SETTINGS_ENCRYPTION_KEY": FAKE_ENV_PASSWORD})
    def test_init_with_env_password(self):
        """Test initializing encryption with environment password."""
        encryption = SettingsEncryption()
        assert encryption.password == FAKE_ENV_PASSWORD

    def test_init_with_default_password(self):
        """Test initializing encryption with default password."""
        with patch.dict("os.environ", {}, clear=True):
            encryption = SettingsEncryption()
            assert encryption.password == FAKE_DEFAULT_PASSWORD

    def test_encrypt_decrypt_round_trip(self):
        """Test encryption and decryption round trip."""
        encryption = SettingsEncryption(password=FAKE_TEST_PASSWORD)

        original_data = FAKE_SENSITIVE_TOKEN
        encrypted = encryption.encrypt(original_data)
        decrypted = encryption.decrypt(encrypted)

        assert encrypted != original_data
        assert decrypted == original_data

    def test_encrypt_empty_data(self):
        """Test encrypting empty data."""
        encryption = SettingsEncryption(password=FAKE_TEST_PASSWORD)

        assert encryption.encrypt("") == ""
        assert encryption.encrypt(None) is None

    def test_decrypt_empty_data(self):
        """Test decrypting empty data."""
        encryption = SettingsEncryption(password=FAKE_TEST_PASSWORD)

        assert encryption.decrypt("") == ""
        assert encryption.decrypt(None) is None

    def test_decrypt_invalid_data(self):
        """Test decrypting invalid encrypted data."""
        encryption = SettingsEncryption(password=FAKE_TEST_PASSWORD)

        # Should return original data if decryption fails (backwards compatibility)
        invalid_data = "not_encrypted_data"
        result = encryption.decrypt(invalid_data)
        assert result == invalid_data

    def test_is_encrypted_valid(self):
        """Test detecting encrypted data."""
        encryption = SettingsEncryption(password=FAKE_TEST_PASSWORD)

        original_data = "test_data"
        encrypted = encryption.encrypt(original_data)

        assert encryption.is_encrypted(encrypted) is True
        assert encryption.is_encrypted(original_data) is False

    def test_is_encrypted_empty(self):
        """Test detecting encryption on empty data."""
        encryption = SettingsEncryption(password=FAKE_TEST_PASSWORD)

        assert encryption.is_encrypted("") is False
        assert encryption.is_encrypted(None) is False


class TestSecurityUtilityFunctions:
    """Test utility functions."""

    def test_get_encryption_singleton(self):
        """Test that get_encryption returns singleton instance."""
        encryption1 = get_encryption()
        encryption2 = get_encryption()
        assert encryption1 is encryption2

    def test_generate_encryption_key(self):
        """Test generating encryption key."""
        key = generate_encryption_key()
        assert isinstance(key, str)
        assert len(key) > 20  # Fernet keys are base64 encoded

    def test_secure_compare_equal(self):
        """Test secure string comparison with equal strings."""
        assert secure_compare("test_string", "test_string") is True

    def test_secure_compare_different(self):
        """Test secure string comparison with different strings."""
        assert secure_compare("test_string", "other_string") is False

    def test_secure_compare_different_length(self):
        """Test secure string comparison with different length strings."""
        assert secure_compare("short", "much_longer_string") is False

    def test_secure_compare_empty(self):
        """Test secure string comparison with empty strings."""
        assert secure_compare("", "") is True
        assert secure_compare("test", "") is False
        assert secure_compare("", "test") is False


class TestValidatorErrorPaths:
    """Test error handling paths in validators."""

    def test_github_token_invalid_sanitization(self):
        """Test GitHub token validation with invalid token that fails sanitization."""
        validator = SettingsValidator()

        # Mock InputSanitizer to raise ValueError
        with patch.object(InputSanitizer, "sanitize_token", side_effect=ValueError("Invalid token format")):
            errors = validator.validate_github_token("invalid<>token")
            assert "Invalid token format" in errors

    def test_gemini_api_key_invalid_sanitization(self):
        """Test Gemini API key validation with invalid key that fails sanitization."""
        validator = SettingsValidator()

        # Mock InputSanitizer to raise ValueError
        with patch.object(InputSanitizer, "sanitize_token", side_effect=ValueError("Invalid API key format")):
            errors = validator.validate_gemini_api_key("invalid<>key")
            assert "Invalid API key format" in errors

    def test_validate_jenkins_url_localhost_warning(self):
        """Test Jenkins URL validation with localhost (should pass through)."""
        validator = SettingsValidator()

        # This should trigger the localhost detection but not add errors
        errors = validator.validate_jenkins_url("http://localhost:8080")
        # Should have HTTP warning but localhost detection just passes
        assert any("HTTP URLs are not secure" in error for error in errors)

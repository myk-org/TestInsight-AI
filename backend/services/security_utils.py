"""Security utilities for TestInsight AI."""

import base64
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SettingsEncryption:
    """Encryption utilities for sensitive settings data."""

    def __init__(self, password: str | None = None):
        """Initialize encryption with password or environment variable.

        Args:
            password: Encryption password. Uses SETTINGS_ENCRYPTION_KEY env var if None.
        """
        self.password = password or os.getenv("SETTINGS_ENCRYPTION_KEY", "default-key-change-me")
        self.salt = b"testinsight_salt"  # In production, use random salt per installation
        self._fernet = self._create_fernet()

    def _create_fernet(self) -> Fernet:
        """Create Fernet encryption instance.

        Returns:
            Fernet encryption instance
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.password.encode() if self.password else b"default"))
        return Fernet(key)

    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data.

        Args:
            data: Plain text data to encrypt

        Returns:
            Base64 encoded encrypted data
        """
        if not data:
            return data

        encrypted = self._fernet.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data.

        Args:
            encrypted_data: Base64 encoded encrypted data

        Returns:
            Decrypted plain text data
        """
        if not encrypted_data:
            return encrypted_data

        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self._fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception:
            # If decryption fails, assume data is not encrypted (for backwards compatibility)
            return encrypted_data

    def is_encrypted(self, data: str) -> bool:
        """Check if data appears to be encrypted.

        Args:
            data: Data to check

        Returns:
            True if data appears to be encrypted
        """
        if not data:
            return False

        try:
            # Try to decode as base64
            base64.urlsafe_b64decode(data.encode())
            # If successful and has typical encrypted data characteristics
            return len(data) > 40 and all(
                c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_="  # pragma: allowlist secret
                for c in data
            )
        except Exception:
            return False


class InputSanitizer:
    """Input sanitization utilities."""

    @staticmethod
    def sanitize_url(url: str) -> str:
        """Sanitize URL input.

        Args:
            url: URL to sanitize

        Returns:
            Sanitized URL
        """
        if not url:
            return url

        # Remove potential script injections
        url = url.strip()

        # Ensure URL has proper protocol
        if url and not url.startswith(("http://", "https://")):
            # Don't auto-add protocol, let validation catch this
            pass

        # Remove any potential script tags or javascript
        dangerous_patterns = ["javascript:", "<script", "</script", "onclick=", "onerror="]
        for pattern in dangerous_patterns:
            if pattern.lower() in url.lower():
                raise ValueError(f"URL contains potentially dangerous content: {pattern}")

        return url

    @staticmethod
    def sanitize_token(token: str) -> str:
        """Sanitize token/API key input.

        Args:
            token: Token to sanitize

        Returns:
            Sanitized token
        """
        if not token:
            return token

        # Remove whitespace
        token = token.strip()

        # Check for suspicious patterns
        if any(char in token for char in ["<", ">", '"', "'", "&"]):
            raise ValueError("Token contains invalid characters")

        return token

    @staticmethod
    def sanitize_username(username: str) -> str:
        """Sanitize username input.

        Args:
            username: Username to sanitize

        Returns:
            Sanitized username
        """
        if not username:
            return username

        # Remove whitespace
        username = username.strip()

        # Check for basic injection patterns
        if any(char in username for char in ["<", ">", '"', "'", "&", ";", "|"]):
            raise ValueError("Username contains invalid characters")

        return username


class SettingsValidator:
    """Enhanced settings validation with security checks."""

    @staticmethod
    def validate_jenkins_url(url: str) -> list[str]:
        """Validate Jenkins URL with security checks.

        Args:
            url: Jenkins URL to validate

        Returns:
            List of validation errors
        """
        errors: list[str] = []

        if not url:
            return errors

        try:
            url = InputSanitizer.sanitize_url(url)
        except ValueError as e:
            errors.append(str(e))
            return errors

        # Basic URL format validation
        if not url.startswith(("http://", "https://")):
            errors.append("Jenkins URL must start with http:// or https://")

        # Security: Warn about HTTP URLs
        if url.startswith("http://"):
            errors.append("Warning: HTTP URLs are not secure. Consider using HTTPS.")

        # Check for localhost/internal URLs in production
        if any(host in url.lower() for host in ["localhost", "127.0.0.1", "192.168.", "10.", "172."]):
            # This might be intentional in development
            pass

        return errors

    @staticmethod
    def validate_github_token(token: str) -> list[str]:
        """Validate GitHub token format.

        Args:
            token: GitHub token to validate

        Returns:
            List of validation errors
        """
        errors: list[str] = []

        if not token:
            return errors

        try:
            token = InputSanitizer.sanitize_token(token)
        except ValueError as e:
            errors.append(str(e))
            return errors

        # Skip validation for encrypted tokens (they will have base64-like format)
        encryption = get_encryption()
        if encryption.is_encrypted(token):
            return errors  # Don't validate encrypted tokens

        # GitHub personal access tokens have specific formats
        # Be more lenient - only warn if format looks suspicious
        if not (
            token.startswith("ghp_")
            or token.startswith("github_pat_")
            or token.startswith("gho_")
            or token.startswith("ghs_")
        ):
            # Don't error on this, just skip validation for legacy tokens
            pass

        # Check minimum length (only for obvious plaintext tokens)
        if len(token) < 10:  # Reduced from 20 to be more lenient
            errors.append("GitHub token appears to be too short")

        return errors

    @staticmethod
    def validate_gemini_api_key(api_key: str) -> list[str]:
        """Validate Gemini API key format.

        Args:
            api_key: Gemini API key to validate

        Returns:
            List of validation errors
        """
        errors: list[str] = []

        if not api_key:
            return errors

        try:
            api_key = InputSanitizer.sanitize_token(api_key)
        except ValueError as e:
            errors.append(str(e))
            return errors

        # Gemini API keys typically start with 'AIzaSy'
        if not api_key.startswith("AIzaSy"):
            errors.append("Gemini API key should start with 'AIzaSy'")

        # Check length
        if len(api_key) != 39:
            errors.append("Gemini API key should be 39 characters long")

        return errors


# Global encryption instance
_encryption: SettingsEncryption | None = None


def get_encryption() -> SettingsEncryption:
    """Get the global encryption instance.

    Returns:
        Settings encryption instance
    """
    global _encryption
    if _encryption is None:
        _encryption = SettingsEncryption()
    return _encryption


def generate_encryption_key() -> str:
    """Generate a new encryption key for settings.

    Returns:
        Base64 encoded encryption key
    """
    return Fernet.generate_key().decode()


def secure_compare(a: str, b: str) -> bool:
    """Securely compare two strings to prevent timing attacks.

    Args:
        a: First string
        b: Second string

    Returns:
        True if strings are equal
    """
    if len(a) != len(b):
        return False

    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)

    return result == 0

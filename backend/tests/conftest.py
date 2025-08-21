"""Pytest configuration and fixtures for backend tests."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_file_operations():
    """Mock file system operations."""
    with (
        patch("builtins.open"),
        patch("pathlib.Path.exists"),
        patch("pathlib.Path.write_text"),
        patch("pathlib.Path.read_text"),
        patch("json.load"),
        patch("json.dump"),
    ):
        yield


# Test constants
FAKE_JENKINS_URL = "https://fake-jenkins.example.com"
FAKE_JENKINS_USERNAME = "testuser"
FAKE_GITHUB_REPO = "https://github.com/testorg/testrepo"
FAKE_REPO_PATH = "/tmp/fake_repo_123"

# Additional test constants for comprehensive token/key management
FAKE_JENKINS_TOKEN = "fake_token_123"  # pragma: allowlist secret
FAKE_GITHUB_TOKEN = "fake_github_token_xyz"  # pragma: allowlist secret
FAKE_GEMINI_API_KEY = "AIzaSyFakeKeyExample123456789"  # pragma: allowlist secret
FAKE_INVALID_API_KEY = "invalid_key_12345678901234567890"  # pragma: allowlist secret
FAKE_INVALID_FORMAT_KEY = "invalid_format_key"  # pragma: allowlist secret
FAKE_COMMIT_HASH = "abc123def456"  # pragma: allowlist secret
FAKE_SHORT_COMMIT = "abc123"  # pragma: allowlist secret
FAKE_TEST_PASSWORD = "test_password"  # pragma: allowlist secret
FAKE_ENV_PASSWORD = "env_password"  # pragma: allowlist secret
FAKE_DEFAULT_PASSWORD = "default-key-change-me"  # pragma: allowlist secret
FAKE_TEST_TOKEN = "test_token"  # pragma: allowlist secret
FAKE_OTHER_TOKEN = "other_token"  # pragma: allowlist secret
FAKE_CUSTOM_TOKEN = "custom_token_xyz"  # pragma: allowlist secret
FAKE_BAD_TOKEN = "bad_token"  # pragma: allowlist secret
FAKE_CUSTOM_API_KEY = "AIzaSyCustomKeyExample123"  # pragma: allowlist secret
FAKE_NEW_API_KEY = "AIzaSyNewKey123"  # pragma: allowlist secret
FAKE_LONG_API_KEY = "AIzaSyTooLongExample1234567890123456789012345678901234567890"  # pragma: allowlist secret
FAKE_SHORT_TOKEN = "fake_token_123456"  # pragma: allowlist secret
FAKE_PADDED_TOKEN = "  fake_token_123  "  # pragma: allowlist secret
FAKE_SENSITIVE_TOKEN = "fake_sensitive_token_123"  # pragma: allowlist secret
FAKE_OLD_TOKEN = "old_token"  # pragma: allowlist secret
FAKE_USER1_TOKEN = "token1"  # pragma: allowlist secret

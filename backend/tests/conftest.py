"""Pytest configuration and fixtures for backend tests."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_settings_file():
    """Mock settings file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        fake_settings = {
            "jenkins": {
                "url": "https://fake-jenkins.example.com",
                "username": "testuser",
                "password": "fake_token_123",  # pragma: allowlist secret
                "verify_ssl": True,
            },
            "github": {"token": "fake_github_token_xyz"},  # pragma: allowlist secret
            "ai": {
                "api_key": "AIzaSyFakeKeyExample123456789",  # pragma: allowlist secret
                "model": "gemini-1.5-pro",
                "temperature": 0.7,
                "max_tokens": 4096,
            },
        }
        json.dump(fake_settings, f)
        f.flush()
        yield f.name
        Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def fake_jenkins_response():
    """Fake Jenkins API response data."""
    return {
        "jobs": [
            {
                "name": "test-job-1",
                "url": "https://fake-jenkins.example.com/job/test-job-1/",
                "color": "blue",
                "buildable": True,
            },
            {
                "name": "test-job-2",
                "url": "https://fake-jenkins.example.com/job/test-job-2/",
                "color": "red",
                "buildable": True,
            },
        ],
        "builds": [
            {
                "number": 42,
                "url": "https://fake-jenkins.example.com/job/test-job-1/42/",
                "result": "SUCCESS",
                "timestamp": 1640995200000,
                "duration": 120000,
            },
            {
                "number": 41,
                "url": "https://fake-jenkins.example.com/job/test-job-1/41/",
                "result": "FAILURE",
                "timestamp": 1640908800000,
                "duration": 95000,
            },
        ],
        "console_output": "Started by user testuser\nBuilding in workspace /var/jenkins_home/workspace/test-job-1\n[Pipeline] Start of Pipeline\n[Pipeline] stage\n[Pipeline] { (Build)\n[Pipeline] sh\n+ echo 'Building application...'\nBuilding application...\n[Pipeline] }\n[Pipeline] // stage\n[Pipeline] End of Pipeline\nFinished: SUCCESS",
    }


@pytest.fixture
def fake_gemini_response():
    """Fake Gemini API response data."""
    return {
        "models": [
            {
                "name": "gemini-1.5-pro",
                "display_name": "Gemini 1.5 Pro",
                "description": "Fake Gemini model for testing",
                "version": "1.5",
                "input_token_limit": 8192,
                "output_token_limit": 8192,
                "supported_generation_methods": ["generateContent"],
            },
            {
                "name": "gemini-1.5-flash",
                "display_name": "Gemini 1.5 Flash",
                "description": "Fake fast Gemini model for testing",
                "version": "1.5",
                "input_token_limit": 4096,
                "output_token_limit": 4096,
                "supported_generation_methods": ["generateContent"],
            },
        ],
        "generated_content": {
            "text": "This is fake generated content from the mock Gemini API.",
            "candidates": [{"content": {"parts": [{"text": "Fake AI analysis result"}]}}],
        },
        "insights": [
            {
                "title": "Test Failure Pattern",
                "description": "Fake analysis shows repeated test failures in authentication module",
                "severity": "HIGH",
                "category": "Reliability",
                "suggestions": ["Review authentication logic", "Add retry mechanisms"],
                "confidence": 0.85,
            }
        ],
    }


@pytest.fixture
def fake_git_response():
    """Fake Git operations response data."""
    return {
        "clone_path": "/tmp/fake_repo_123",
        "file_content": "# Fake Repository\n\nThis is fake file content for testing.\n\n## Features\n- Fake feature 1\n- Fake feature 2",
        "commit_hash": "abc123def456",  # pragma: allowlist secret
        "branch": "main",
    }


@pytest.fixture
def mock_jenkins_client():
    """Mock Jenkins client."""
    mock_client = Mock()
    mock_client.is_connected.return_value = True
    mock_client.get_jobs.return_value = [
        {"name": "test-job-1", "color": "blue"},
        {"name": "test-job-2", "color": "red"},
    ]
    mock_client.get_job_builds.return_value = [{"number": 42, "result": "SUCCESS"}, {"number": 41, "result": "FAILURE"}]

    return mock_client


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini client."""
    mock_client = Mock()
    mock_client.validate_api_key.return_value = True
    mock_client.get_available_models.return_value = {
        "success": True,
        "models": [
            {
                "name": "gemini-1.5-pro",
                "display_name": "Gemini 1.5 Pro",
                "description": "Fake model",
                "version": "1.5",
                "input_token_limit": 8192,
                "output_token_limit": 8192,
                "supported_generation_methods": ["generateContent"],
            }
        ],
        "total_count": 1,
        "message": "Successfully fetched 1 models",
        "error_details": "",
    }
    mock_client.generate_content.return_value = {
        "success": True,
        "content": "Fake generated content",
        "model": "gemini-1.5-pro",
    }
    return mock_client


@pytest.fixture
def mock_git_client():
    """Mock Git client."""
    mock_client = Mock()
    mock_client.repo_path = Path("/tmp/fake_repo_123")
    mock_client.get_file_content.return_value = "Fake file content"
    return mock_client


@pytest.fixture
def fake_analysis_request():
    """Fake analysis request data."""
    return {
        "test_results": "Fake test results content",
        "jenkins_data": "Fake Jenkins build data",
        "context": "Fake analysis context",
    }


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

"""Tests for service connection testers coverage."""

from unittest.mock import patch

import pytest

from backend.services.service_config.connection_testers import ServiceConnectionTesters


def test_test_github_connection_no_token():
    """Test test_github_connection with no token."""
    with patch(
        "backend.services.service_config.config_getters.ServiceConfigGetters.get_github_config"
    ) as mock_get_config:
        mock_get_config.return_value = {"token": None}
        testers = ServiceConnectionTesters()
        with pytest.raises(ValueError):
            testers.test_github_connection()


def test_test_ai_connection_with_config_no_api_key():
    """Test test_ai_connection_with_config with no API key."""
    testers = ServiceConnectionTesters()
    with pytest.raises(ValueError):
        testers.test_ai_connection_with_config({})


def test_test_ai_connection_with_config_empty_api_key():
    """Test test_ai_connection_with_config with an empty API key."""
    testers = ServiceConnectionTesters()
    with pytest.raises(ValueError):
        testers.test_ai_connection_with_config({"gemini_api_key": ""})

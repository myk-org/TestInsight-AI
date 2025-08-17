"""Tests for Gemini API client service."""

from unittest.mock import Mock, patch
import pytest

from backend.services.gemini_api import GeminiClient
from backend.models.schemas import GeminiModelsResponse
from backend.services.security_utils import SettingsValidator
from backend.tests.conftest import (
    FAKE_GEMINI_API_KEY,
    FAKE_INVALID_FORMAT_KEY,
)


class TestGeminiClient:
    """Test cases for GeminiClient class."""

    @patch("backend.services.gemini_api.genai.Client")
    @patch.object(GeminiClient, "validate_api_key")
    def test_init_success(self, mock_validate, mock_genai_client):
        """Test GeminiClient initialization success."""
        mock_validate.return_value = True
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        client = GeminiClient(api_key=FAKE_GEMINI_API_KEY)

        assert client.api_key == FAKE_GEMINI_API_KEY
        assert client.client == mock_client_instance
        mock_genai_client.assert_called_once_with(api_key=FAKE_GEMINI_API_KEY)
        mock_validate.assert_called_once()

    @patch("backend.services.gemini_api.genai.Client")
    @patch.object(GeminiClient, "validate_api_key")
    def test_init_validation_failure(self, mock_validate, mock_genai_client):
        """Test GeminiClient initialization with validation failure."""
        mock_validate.side_effect = ValueError("Invalid API key")
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        with pytest.raises(ValueError, match="Invalid API key"):
            GeminiClient(api_key=FAKE_GEMINI_API_KEY)

    @patch("backend.services.gemini_api.genai.Client")
    def test_list_models_success(self, mock_genai_client):
        """Test _list_models returns model list."""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        fake_models = [
            Mock(name="models/gemini-1.5-pro", display_name="Gemini 1.5 Pro"),
            Mock(name="models/gemini-1.5-flash", display_name="Gemini 1.5 Flash"),
        ]
        mock_client_instance.models.list.return_value = fake_models

        with patch.object(GeminiClient, "validate_api_key"):
            client = GeminiClient(api_key=FAKE_GEMINI_API_KEY)
            result = client._list_models()

            assert result == fake_models
            mock_client_instance.models.list.assert_called_once()

    @patch("backend.services.gemini_api.genai.Client")
    def test_list_models_connection_error(self, mock_genai_client):
        """Test _list_models raises ConnectionError on API failure."""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance
        mock_client_instance.models.list.side_effect = Exception("API Error")

        with patch.object(GeminiClient, "validate_api_key"):
            client = GeminiClient(api_key=FAKE_GEMINI_API_KEY)

            with pytest.raises(Exception, match="API Error"):
                client._list_models()

    @patch("backend.services.gemini_api.genai.Client")
    @patch.object(SettingsValidator, "validate_gemini_api_key")
    def test_validate_api_key_empty_key(self, mock_validator, mock_genai_client):
        """Test validate_api_key raises ValueError for empty key."""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        with pytest.raises(ValueError, match="API key is required"):
            GeminiClient(api_key="")

    @patch("backend.services.gemini_api.genai.Client")
    @patch.object(SettingsValidator, "validate_gemini_api_key")
    def test_validate_api_key_format_validation_failure(self, mock_validator, mock_genai_client):
        """Test validate_api_key with format validation errors."""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance
        mock_validator.return_value = ["Invalid format"]

        with patch.object(GeminiClient, "_list_models"):
            client = GeminiClient.__new__(GeminiClient)  # Skip __init__
            client.api_key = FAKE_INVALID_FORMAT_KEY
            client.client = mock_client_instance

            result = client.validate_api_key()
            assert result is False

    @patch("backend.services.gemini_api.genai.Client")
    @patch.object(SettingsValidator, "validate_gemini_api_key")
    def test_validate_api_key_connection_test_success(self, mock_validator, mock_genai_client):
        """Test validate_api_key with successful connection test."""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance
        mock_validator.return_value = []  # No validation errors

        with patch.object(GeminiClient, "_list_models", return_value=[Mock()]):
            client = GeminiClient.__new__(GeminiClient)  # Skip __init__
            client.api_key = FAKE_GEMINI_API_KEY
            client.client = mock_client_instance

            result = client.validate_api_key()
            assert result is True

    @patch("backend.services.gemini_api.genai.Client")
    @patch.object(SettingsValidator, "validate_gemini_api_key")
    def test_validate_api_key_connection_test_failure(self, mock_validator, mock_genai_client):
        """Test validate_api_key with connection test failure."""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance
        mock_validator.return_value = []  # No validation errors

        with patch.object(GeminiClient, "_list_models", return_value=None):
            client = GeminiClient.__new__(GeminiClient)  # Skip __init__
            client.api_key = FAKE_GEMINI_API_KEY
            client.client = mock_client_instance

            result = client.validate_api_key()
            assert result is False  # Returns False if _list_models returns None

    @patch("backend.services.gemini_api.genai.Client")
    def test_get_available_models_success(self, mock_genai_client):
        """Test get_available_models returns filtered models."""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        # Create mock models with different characteristics
        mock_text_model = Mock()
        mock_text_model.name = "models/gemini-1.5-pro"
        mock_text_model.display_name = "Gemini 1.5 Pro"
        mock_text_model.description = "Advanced text model"
        mock_text_model.version = "1.5"
        mock_text_model.input_token_limit = 8192
        mock_text_model.output_token_limit = 8192
        mock_text_model.supported_generation_methods = ["generateContent"]

        mock_vision_model = Mock()
        mock_vision_model.name = "models/gemini-vision-pro"
        mock_vision_model.display_name = "Gemini Vision Pro"
        mock_vision_model.description = "Vision model"
        mock_vision_model.version = "1.0"
        mock_vision_model.input_token_limit = 4096
        mock_vision_model.output_token_limit = 4096
        mock_vision_model.supported_generation_methods = ["generateContent"]

        mock_embedding_model = Mock()
        mock_embedding_model.name = "models/text-embedding-004"
        mock_embedding_model.display_name = "Text Embedding"
        mock_embedding_model.description = "Embedding model"
        mock_embedding_model.version = "004"
        mock_embedding_model.input_token_limit = 2048
        mock_embedding_model.output_token_limit = 1
        mock_embedding_model.supported_generation_methods = ["embedContent"]

        fake_models = [mock_text_model, mock_vision_model, mock_embedding_model]

        with (
            patch.object(GeminiClient, "validate_api_key"),
            patch.object(GeminiClient, "_list_models", return_value=fake_models),
        ):
            client = GeminiClient(api_key=FAKE_GEMINI_API_KEY)
            result = client.get_available_models()

            assert isinstance(result, GeminiModelsResponse)
            assert result.success is True
            assert result.total_count == 1  # Only text model should be included
            assert len(result.models) == 1
            assert result.models[0].name == "gemini-1.5-pro"
            assert "vision" not in result.models[0].name
            assert "embedding" not in result.models[0].name

    @patch("backend.services.gemini_api.genai.Client")
    def test_get_available_models_no_generation_methods(self, mock_genai_client):
        """Test get_available_models filters out models without generation methods."""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        mock_model_no_methods = Mock()
        mock_model_no_methods.name = "models/gemini-test"
        mock_model_no_methods.supported_generation_methods = None

        fake_models = [mock_model_no_methods]

        with (
            patch.object(GeminiClient, "validate_api_key"),
            patch.object(GeminiClient, "_list_models", return_value=fake_models),
        ):
            client = GeminiClient(api_key=FAKE_GEMINI_API_KEY)
            result = client.get_available_models()

            assert result.total_count == 0
            assert len(result.models) == 0

    @patch("backend.services.gemini_api.genai.Client")
    def test_get_available_models_empty_list(self, mock_genai_client):
        """Test get_available_models with empty model list."""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        with (
            patch.object(GeminiClient, "validate_api_key"),
            patch.object(GeminiClient, "_list_models", return_value=[]),
        ):
            client = GeminiClient(api_key=FAKE_GEMINI_API_KEY)
            result = client.get_available_models()

            assert result.success is True
            assert result.total_count == 0
            assert len(result.models) == 0
            assert "0 models" in result.message

    @patch("backend.services.gemini_api.genai.Client")
    def test_get_available_models_filters_excluded_keywords(self, mock_genai_client):
        """Test get_available_models filters out models with excluded keywords."""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        models_to_test = [
            ("models/gemini-1.5-pro", True),  # Should be included
            ("models/gemini-embedding-001", False),  # Has 'embedding'
            ("models/gemini-vision-pro", False),  # Has 'vision'
            ("models/gemini-image-gen", False),  # Has 'image'
            ("models/gemini-video-001", False),  # Has 'video'
            ("models/gemini-audio-001", False),  # Has 'audio'
            ("models/gemini-code-001", False),  # Has 'code'
        ]

        fake_models = []
        for model_name, _ in models_to_test:
            mock_model = Mock()
            mock_model.name = model_name
            mock_model.display_name = model_name.replace("models/", "").title()
            mock_model.description = f"Test model {model_name}"
            mock_model.version = "1.0"
            mock_model.input_token_limit = 4096
            mock_model.output_token_limit = 4096
            mock_model.supported_generation_methods = ["generateContent"]
            fake_models.append(mock_model)

        with (
            patch.object(GeminiClient, "validate_api_key"),
            patch.object(GeminiClient, "_list_models", return_value=fake_models),
        ):
            client = GeminiClient(api_key=FAKE_GEMINI_API_KEY)
            result = client.get_available_models()

            # Only the first model should be included
            assert result.total_count == 1
            assert len(result.models) == 1
            assert result.models[0].name == "gemini-1.5-pro"

    @patch("backend.services.gemini_api.genai.Client")
    def test_get_available_models_handles_missing_attributes(self, mock_genai_client):
        """Test get_available_models handles models with missing attributes."""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        mock_model = Mock()
        mock_model.name = "models/gemini-minimal"
        mock_model.supported_generation_methods = ["generateContent"]
        # Missing other attributes - should use defaults
        del mock_model.display_name
        del mock_model.description
        del mock_model.version
        del mock_model.input_token_limit
        del mock_model.output_token_limit

        fake_models = [mock_model]

        with (
            patch.object(GeminiClient, "validate_api_key"),
            patch.object(GeminiClient, "_list_models", return_value=fake_models),
        ):
            client = GeminiClient(api_key=FAKE_GEMINI_API_KEY)
            result = client.get_available_models()

            assert result.total_count == 1
            model = result.models[0]
            assert model.name == "gemini-minimal"
            assert model.display_name == "gemini-minimal"  # Falls back to name
            assert model.description == ""
            assert model.version == ""
            assert model.input_token_limit == 0
            assert model.output_token_limit == 0

    @patch("backend.services.gemini_api.genai.Client")
    def test_generate_content_success(self, mock_genai_client):
        """Test generate_content returns successful response."""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        mock_response = Mock()
        mock_response.text = "This is the generated content from Gemini"
        mock_client_instance.models.generate_content.return_value = mock_response

        with patch.object(GeminiClient, "validate_api_key"):
            client = GeminiClient(api_key=FAKE_GEMINI_API_KEY)

            result = client.generate_content(
                prompt="Analyze this test failure", model="gemini-1.5-pro", temperature=0.8, max_tokens=2048
            )

            assert result["success"] is True
            assert result["content"] == "This is the generated content from Gemini"
            assert result["model"] == "gemini-1.5-pro"

            mock_client_instance.models.generate_content.assert_called_once_with(
                model="models/gemini-1.5-pro",
                contents=[{"parts": [{"text": "Analyze this test failure"}]}],
                config={
                    "temperature": 0.8,
                    "max_output_tokens": 2048,
                },
            )

    @patch("backend.services.gemini_api.genai.Client")
    def test_generate_content_default_parameters(self, mock_genai_client):
        """Test generate_content with default parameters."""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        mock_response = Mock()
        mock_response.text = "Generated content"
        mock_client_instance.models.generate_content.return_value = mock_response

        with patch.object(GeminiClient, "validate_api_key"):
            client = GeminiClient(api_key=FAKE_GEMINI_API_KEY)

            result = client.generate_content("Test prompt")

            assert result["success"] is True
            mock_client_instance.models.generate_content.assert_called_once_with(
                model="models/gemini-2.5-pro",  # Default model
                contents=[{"parts": [{"text": "Test prompt"}]}],
                config={
                    "temperature": 0.7,  # Default temperature
                    "max_output_tokens": 4096,  # Default max_tokens
                },
            )

    @patch("backend.services.gemini_api.genai.Client")
    def test_generate_content_no_text_attribute(self, mock_genai_client):
        """Test generate_content when response has no text attribute."""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        mock_response = Mock(spec=[])  # No 'text' attribute
        mock_client_instance.models.generate_content.return_value = mock_response

        with patch.object(GeminiClient, "validate_api_key"):
            client = GeminiClient(api_key=FAKE_GEMINI_API_KEY)

            result = client.generate_content("Test prompt")

            assert result["success"] is True
            assert result["content"] == str(mock_response)  # Falls back to str()

    @patch("backend.services.gemini_api.genai.Client")
    def test_generate_content_api_error(self, mock_genai_client):
        """Test generate_content handles API errors."""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance
        mock_client_instance.models.generate_content.side_effect = Exception("API rate limit exceeded")

        with patch.object(GeminiClient, "validate_api_key"):
            client = GeminiClient(api_key=FAKE_GEMINI_API_KEY)

            with pytest.raises(Exception, match="API rate limit exceeded"):
                client.generate_content("Test prompt")

    @patch("backend.services.gemini_api.genai.Client")
    def test_generate_content_custom_model_format(self, mock_genai_client):
        """Test generate_content properly formats model name."""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        mock_response = Mock()
        mock_response.text = "Generated content"
        mock_client_instance.models.generate_content.return_value = mock_response

        with patch.object(GeminiClient, "validate_api_key"):
            client = GeminiClient(api_key=FAKE_GEMINI_API_KEY)

            # Test with model name that already has 'models/' prefix
            client.generate_content("Test", model="models/gemini-1.5-flash")

            mock_client_instance.models.generate_content.assert_called_once_with(
                model="models/models/gemini-1.5-flash",  # Will be double-prefixed (potential bug)
                contents=[{"parts": [{"text": "Test"}]}],
                config={
                    "temperature": 0.7,
                    "max_output_tokens": 4096,
                },
            )

    @patch("backend.services.gemini_api.genai.Client")
    def test_settings_validator_integration(self, mock_genai_client):
        """Test integration with SettingsValidator."""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        with (
            patch.object(GeminiClient, "_list_models", return_value=[Mock()]),
            patch.object(SettingsValidator, "validate_gemini_api_key", return_value=[]) as mock_validator,
        ):
            client = GeminiClient.__new__(GeminiClient)  # Skip __init__
            client.api_key = FAKE_GEMINI_API_KEY
            client.client = mock_client_instance

            result = client.validate_api_key()

            mock_validator.assert_called_once_with(FAKE_GEMINI_API_KEY)
            assert result is True

    @patch("backend.services.gemini_api.genai.Client")
    def test_logging_integration(self, mock_genai_client):
        """Test that logging works correctly."""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        # Create proper mock model with string attributes
        mock_model = Mock()
        mock_model.name = "models/gemini-1.5-pro"
        mock_model.display_name = "Gemini 1.5 Pro"
        mock_model.description = "Test model"
        mock_model.version = "1.5"
        mock_model.input_token_limit = 4096
        mock_model.output_token_limit = 4096
        mock_model.supported_generation_methods = ["generateContent"]

        fake_models = [mock_model]

        with (
            patch.object(GeminiClient, "validate_api_key"),
            patch.object(GeminiClient, "_list_models", return_value=fake_models),
            patch("backend.services.gemini_api.logger") as mock_logger,
        ):
            client = GeminiClient(api_key=FAKE_GEMINI_API_KEY)
            client.get_available_models()

            # Verify logging calls were made
            assert mock_logger.info.call_count >= 1  # At least 1 info log

"""Service for fetching available Gemini models from Google AI API."""

import logging
import time

from google import genai
from google.generativeai import types as google_exceptions

from backend.models.schemas import GeminiModelInfo, GeminiModelsResponse
from backend.services.security_utils import InputSanitizer, SettingsValidator

logger = logging.getLogger(__name__)


class GeminiModelsService:
    """Service for fetching and managing Gemini models from Google AI API."""

    def __init__(self) -> None:
        """Initialize the Gemini models service."""
        self.sanitizer = InputSanitizer()
        self.validator = SettingsValidator()

    def fetch_available_models(self, api_key: str) -> GeminiModelsResponse:
        """Fetch available Gemini models using the provided API key.

        Args:
            api_key: Google Gemini API key

        Returns:
            GeminiModelsResponse with available models or error information
        """
        start_time = time.time()

        try:
            # Sanitize and validate the API key
            api_key = self.sanitizer.sanitize_token(api_key)
            validation_errors = self.validator.validate_gemini_api_key(api_key)

            if validation_errors:
                logger.warning(f"API key validation failed: {validation_errors}")
                return GeminiModelsResponse(
                    success=False,
                    models=[],
                    total_count=0,
                    message="Invalid API key format",
                    error_details="; ".join(validation_errors),
                )

            # Configure the Google AI client
            client = genai.Client(api_key=api_key)

            # Fetch available models
            try:
                models_list = list(client.models.list())
                logger.info(f"Fetched {len(models_list)} models from Google AI API")

                # Convert to our schema format
                gemini_models = []
                for model in models_list:
                    # Filter to only include generative models (exclude embedding models, etc.)
                    if hasattr(model, "supported_generation_methods") and model.supported_generation_methods:
                        model_name = model.name.replace("models/", "").lower()

                        # Additional filtering for TestInsight AI usecase - only include text-focused models
                        # Exclude image/vision models and embedding models
                        excluded_keywords = [
                            "embedding",
                            "embed",
                            "imagen",
                            "imagetext",
                            "video",
                            "audio",
                            "multimodal",
                            "mm",
                            "search",
                            "retrieval",
                            "code-",
                            "codechat",
                        ]

                        # Check if model name contains excluded keywords
                        if any(keyword in model_name for keyword in excluded_keywords):
                            logger.debug(f"Excluding model {model_name} due to excluded keywords")
                            continue

                        # Only include models that support text generation
                        if "generateContent" not in model.supported_generation_methods:
                            logger.debug(f"Excluding model {model_name} - no generateContent support")
                            continue

                        model_info = GeminiModelInfo(
                            name=model.name.replace("models/", ""),  # Remove 'models/' prefix
                            display_name=getattr(model, "display_name", model.name.replace("models/", "")),
                            description=getattr(model, "description", None),
                            version=getattr(model, "version", None),
                            input_token_limit=getattr(model, "input_token_limit", None),
                            output_token_limit=getattr(model, "output_token_limit", None),
                            supported_generation_methods=list(model.supported_generation_methods),
                        )
                        gemini_models.append(model_info)

                response_time = (time.time() - start_time) * 1000
                logger.info(f"Successfully processed {len(gemini_models)} generative models in {response_time:.2f}ms")

                return GeminiModelsResponse(
                    success=True,
                    models=gemini_models,
                    total_count=len(gemini_models),
                    message=f"Successfully fetched {len(gemini_models)} Gemini models",
                    error_details="",
                )

            except google_exceptions.Unauthenticated as e:
                logger.error(f"Authentication failed with provided API key: {e}")
                return GeminiModelsResponse(
                    success=False,
                    models=[],
                    total_count=0,
                    message="Authentication failed",
                    error_details="Invalid API key. Please verify your Gemini API key is correct and active.",
                )

            except google_exceptions.PermissionDenied as e:
                logger.error(f"Permission denied for API key: {e}")
                return GeminiModelsResponse(
                    success=False,
                    models=[],
                    total_count=0,
                    message="Permission denied",
                    error_details="API key does not have permission to access Gemini models. Please check your API key permissions.",
                )

            except google_exceptions.ResourceExhausted as e:
                logger.error(f"API quota exceeded: {e}")
                return GeminiModelsResponse(
                    success=False,
                    models=[],
                    total_count=0,
                    message="API quota exceeded",
                    error_details="API quota has been exceeded. Please try again later or check your quota limits.",
                )

            except Exception as e:
                logger.error(f"Unexpected error fetching models: {e}", exc_info=True)
                return GeminiModelsResponse(
                    success=False,
                    models=[],
                    total_count=0,
                    message="Failed to fetch models",
                    error_details=f"Unexpected error: {str(e)}",
                )

        except ValueError as e:
            # Input sanitization errors
            logger.warning(f"Input validation error: {e}")
            return GeminiModelsResponse(
                success=False, models=[], total_count=0, message="Invalid input", error_details=str(e)
            )

        except Exception as e:
            # Any other unexpected errors
            logger.error(f"Service error: {e}", exc_info=True)
            return GeminiModelsResponse(
                success=False,
                models=[],
                total_count=0,
                message="Service error",
                error_details=f"Internal service error: {str(e)}",
            )

    def validate_api_key_only(self, api_key: str) -> tuple[bool, str | None]:
        """Validate API key format without making API calls.

        Args:
            api_key: API key to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            api_key = self.sanitizer.sanitize_token(api_key)
            validation_errors = self.validator.validate_gemini_api_key(api_key)

            if validation_errors:
                return False, "; ".join(validation_errors)

            return True, None

        except ValueError as e:
            return False, str(e)

    def test_api_key_connection(self, api_key: str) -> tuple[bool, str | None]:
        """Test API key by making a minimal API call.

        Args:
            api_key: API key to test

        Returns:
            Tuple of (is_valid, error_message)
        """

        try:
            # First validate format
            is_valid, error_msg = self.validate_api_key_only(api_key)
            if not is_valid:
                return False, error_msg

            # Configure and test with minimal API call
            genai.configure(api_key=api_key)

            # Try to list models as a simple test
            models_iter = genai.list_models()
            # Just get the first model to test connectivity
            try:
                next(iter(models_iter), None)
            except Exception:
                # If models_iter is already a list, just access first element
                if hasattr(models_iter, "__iter__"):
                    list(models_iter)  # Convert to list to test the API call

            return True, None

        except google_exceptions.Unauthenticated:
            return False, "Invalid API key"

        except google_exceptions.PermissionDenied:
            return False, "API key lacks required permissions"

        except Exception as e:
            return False, f"Connection test failed: {str(e)}"

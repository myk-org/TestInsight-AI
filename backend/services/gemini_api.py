"""Gemini API client using google-genai library."""

import logging
from typing import Any

from google import genai

from backend.models.schemas import GeminiModelInfo, GeminiModelsResponse
from backend.services.security_utils import SettingsValidator

logger = logging.getLogger(__name__)


class GeminiClient:
    """Gemini client for all AI operations using google-genai."""

    def __init__(self, api_key: str):
        """Initialize Gemini client.

        Args:
            api_key: Google Gemini API key

        Raises:
            ValueError: If API key is invalid
        """
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.validate_api_key()

    def _list_models(self) -> list[Any]:
        """List models from Gemini API.

        Returns:
            List of models

        Raises:
            ConnectionError: If API call fails
        """
        return list(self.client.models.list())

    def validate_api_key(self) -> bool:
        """Validate API key format and connection."""
        # First validate format
        if not self.api_key:
            raise ValueError("API key is required")

        # Use SettingsValidator for format validation
        validator = SettingsValidator()
        validation_errors = validator.validate_gemini_api_key(self.api_key)

        if validation_errors:
            return False

        # Test connection by listing models
        return self._list_models() is not None

    def get_available_models(self) -> GeminiModelsResponse:
        """Get list of available Gemini models.

        Returns:
            GeminiModelsResponse with models list or error
        """
        # Fetch available models
        models_list = self._list_models()
        logger.info(f"Fetched {len(models_list)} models from Google AI API")

        # Convert to our schema format
        gemini_models = []
        for model in models_list:
            # Filter to only include generative models
            if hasattr(model, "supported_generation_methods") and model.supported_generation_methods:
                model_name = model.name.replace("models/", "").lower()

                # Filter for text-focused models only
                excluded_keywords = [
                    "embedding",
                    "vision",
                    "image",
                    "video",
                    "audio",
                    "code",
                ]

                if not any(keyword in model_name for keyword in excluded_keywords):
                    gemini_models.append(
                        GeminiModelInfo(
                            name=model_name,
                            display_name=getattr(model, "display_name", model_name),
                            description=getattr(model, "description", ""),
                            version=getattr(model, "version", ""),
                            input_token_limit=getattr(model, "input_token_limit", 0),
                            output_token_limit=getattr(model, "output_token_limit", 0),
                            supported_generation_methods=model.supported_generation_methods or [],
                        )
                    )

        logger.info(f"Filtered to {len(gemini_models)} suitable models for TestInsight AI")

        return GeminiModelsResponse(
            success=True,
            models=gemini_models,
            total_count=len(gemini_models),
            message=f"Successfully fetched {len(gemini_models)} models",
            error_details="",
        )

    def generate_content(
        self, prompt: str, model: str = "gemini-2.5-pro", temperature: float = 0.7, max_tokens: int = 4096
    ) -> dict[str, Any]:
        """Generate content using Gemini model.

        Args:
            prompt: Input prompt for generation
            model: Model name to use
            temperature: Generation temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Dictionary with generated content or error
        """
        # Generate content
        response = self.client.models.generate_content(
            model=f"models/{model}",
            contents=[{"parts": [{"text": prompt}]}],
            config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
        )

        return {
            "success": True,
            "content": response.text if hasattr(response, "text") else str(response),
            "model": model,
        }

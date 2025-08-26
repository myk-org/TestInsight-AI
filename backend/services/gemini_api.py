"""Gemini API client using google-genai library."""

import logging
import os
import time
from typing import Any

from google import genai

from backend.models.schemas import GeminiModelInfo, GeminiModelsResponse
from backend.services.security_utils import SettingsValidator

logger = logging.getLogger(__name__)


class GeminiClient:
    """Gemini client for all AI operations using google-genai."""

    def __init__(
        self,
        api_key: str,
        *,
        default_model: str | None = None,
        default_temperature: float | None = None,
        default_max_tokens: int | None = None,
    ):
        """Initialize Gemini client with API key.

        Args:
            api_key: Google Gemini API key

        Raises:
            ValueError: If API key is not provided or invalid
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key is required")

        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)

        # Defaults from settings (optional)
        self.default_model = (default_model or "gemini-2.5-pro").strip()
        self.default_temperature = default_temperature if default_temperature is not None else 0.7
        self.default_max_tokens = default_max_tokens if default_max_tokens is not None else 4096

        # Retry/backoff configuration (env-driven)
        self.retry_attempts = int(os.getenv("GENAI_RETRY_ATTEMPTS", "1"))
        self.retry_backoff_ms = int(os.getenv("GENAI_RETRY_BACKOFF_MS", "250"))

        # Validate connection
        self.validate_connection()

    def _list_models(self) -> list[Any]:
        """List models from Gemini API.

        Returns:
            List of models

        Raises:
            ConnectionError: If API call fails
        """
        try:
            models = list(self.client.models.list())
            logger.info(f"Raw models list returned {len(models)} models")
            return models
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            raise ConnectionError(f"Failed to list models: {e}") from e

    def validate_connection(self) -> bool:
        """Validate API key format and connection."""
        # Validate API key format
        validator = SettingsValidator()
        validation_errors = validator.validate_gemini_api_key(self.api_key)

        if validation_errors:
            raise ValueError(f"Invalid API key format: {'; '.join(validation_errors)}")

        # Test connection by listing models
        try:
            return self._list_models() is not None
        except Exception as e:
            logger.error(f"Authentication validation failed: {e}")
            raise ValueError(f"Failed to validate authentication: {e}")

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
            model_name = model.name.replace("models/", "").lower()

            # Filter for known generative models based on name patterns
            # Since supported_generation_methods might not be available, use name-based filtering
            generative_patterns = [
                "gemini-1.5-pro",
                "gemini-1.5-flash",
                "gemini-2.0-flash",
                "gemini-2.5-pro",
                "gemini-2.5-flash",
                "gemini-exp",
                "gemini-pro",
            ]

            # Check if this is a generative model by name pattern
            is_generative = any(pattern in model_name for pattern in generative_patterns)

            if is_generative:
                # Updated filter for text-focused models - exclude multimodal/specialized models
                excluded_keywords = [
                    "embedding",
                    "vision",
                    "image",
                    "video",
                    "audio",
                    "tts",  # Text-to-speech
                    "thinking",  # Thinking models might not be suitable for general use
                ]

                is_excluded = any(keyword in model_name for keyword in excluded_keywords)

                if not is_excluded:
                    gemini_models.append(
                        GeminiModelInfo(
                            name=model_name,
                            display_name=getattr(model, "display_name", model_name),
                            description=getattr(model, "description", ""),
                            version=getattr(model, "version", ""),
                            input_token_limit=getattr(model, "input_token_limit", 0),
                            output_token_limit=getattr(model, "output_token_limit", 0),
                            supported_generation_methods=getattr(model, "supported_generation_methods", []),
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
        self,
        prompt: str,
        model: str = "gemini-2.5-pro",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        *,
        response_mime_type: str | None = None,
        response_schema: Any | None = None,
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
        # Determine effective parameters using client defaults when appropriate
        effective_model = (model or self.default_model).strip()
        effective_temperature = temperature if temperature is not None else self.default_temperature
        effective_max_tokens = max_tokens if max_tokens is not None else self.default_max_tokens

        # Normalize model to ensure a single 'models/' prefix
        normalized_model = (
            effective_model if str(effective_model).startswith("models/") else f"models/{effective_model}"
        )

        # Generate content with basic retry/backoff for transient failures (opt-in via env)
        attempts = max(1, self.retry_attempts)
        for attempt in range(1, attempts + 1):
            try:
                config: dict[str, Any] = {
                    "temperature": effective_temperature,
                    "max_output_tokens": effective_max_tokens,
                }
                # Encourage strict machine-readable output when requested
                if response_mime_type:
                    config["response_mime_type"] = response_mime_type
                if response_schema is not None:
                    config["response_schema"] = response_schema

                # Use kwargs to avoid strict typing issues in stubs
                response = self.client.models.generate_content(
                    model=normalized_model,
                    contents=[{"parts": [{"text": prompt}]}],
                    config=config,
                )
                break
            except Exception as e:  # pragma: no cover - exercised via higher-level tests/mocks
                # Heuristic for transient errors
                message = str(e).lower()
                is_transient = any(k in message for k in ["429", "quota", "rate", "timeout", "temporarily"])
                if attempt >= attempts or not is_transient:
                    raise
                time.sleep((self.retry_backoff_ms / 1000.0) * (2 ** (attempt - 1)))

        # Normalize response content to a safe string to avoid None.strip errors downstream
        raw_text = getattr(response, "text", None)
        try:
            if isinstance(raw_text, str):
                content_str = raw_text
            elif isinstance(raw_text, bytes):
                content_str = raw_text.decode("utf-8", errors="ignore")
            elif raw_text is None:
                content_str = str(response)
            else:
                # Handle other non-str types by converting to string
                content_str = str(raw_text)
        except Exception:  # pragma: no cover - defensive
            content_str = str(response)

        return {
            "success": True,
            "content": str(content_str) if content_str is not None else "",
            "model": effective_model,
        }

"""AI models endpoints for TestInsight AI."""

import logging

from fastapi import APIRouter, HTTPException, Body

from backend.models.schemas import GeminiModelsResponse, AIRequest, KeyValidationResponse
from backend.services.service_config.client_creators import ServiceClientCreators
from backend.services.security_utils import SettingsValidator

router = APIRouter(prefix="/ai", tags=["ai"])
logger = logging.getLogger(__name__)

# Error keyword mapping for API error status code classification
# Order matters: more specific errors should come first
ERROR_KEYWORD_MAPPING = {
    401: [  # Authentication errors
        "invalid api key",
        "authentication failed",
        "unauthorized",
        "api key",
        r"\bauth\b",  # Word boundary matching for single word
        "credential",
        "invalid token",
        "token expired",
    ],
    403: [  # Permission/access errors
        "permission denied",
        "access denied",
        "forbidden",
        "not allowed",
        "insufficient permissions",
    ],
    429: [  # Rate limiting/quota errors
        "quota exceeded",
        "rate limit",
        "too many requests",
        r"\bquota\b",  # Word boundary matching for single word
        r"\brate\b",  # Word boundary matching for single word
        "throttle",
        "quota limit",
    ],
    400: [  # Bad request errors
        "invalid input",
        "bad request",
        "malformed",
        "invalid request",
        "validation error",
        "invalid parameter",
    ],
    503: [  # Service unavailable errors
        "service unavailable",
        "temporarily unavailable",
        "maintenance",
        "overloaded",
        "server busy",
    ],
    504: [  # Timeout errors
        "timeout",
        "timed out",
        "deadline exceeded",
    ],
}


def classify_error_status_code(error_message: str) -> int | None:
    """Classify error message to appropriate HTTP status code.

    Args:
        error_message: Error message to classify (will be converted to lowercase)

    Returns:
        HTTP status code if error pattern matches, None otherwise
    """
    if not error_message:
        return None

    error_lower = error_message.lower().strip()
    if not error_lower:
        return None

    # Find the first matching status code using module constant
    for status_code, keywords in ERROR_KEYWORD_MAPPING.items():
        for keyword in keywords:
            # Handle regex patterns for word boundary matching
            if keyword.startswith(r"\b") and keyword.endswith(r"\b"):
                import re

                if re.search(keyword, error_lower):
                    return status_code
            # Handle regular substring matching
            elif keyword in error_lower:
                return status_code

    return None


def _merge_and_validate_api_key(query_api_key: str | None, request_body: AIRequest | None) -> str | None:
    """Merge and validate API key from query parameter and request body.

    API Key Precedence (intentional design):
    1. Query parameter (?api_key=...) is used as default
    2. Request body api_key field overrides query parameter when present
    This follows REST API conventions where body parameters have higher precedence.

    Args:
        query_api_key: API key from query parameter
        request_body: Request body containing optional API key

    Returns:
        Validated API key or None

    Raises:
        HTTPException: If API key format is invalid (400 status)
    """
    # Apply precedence rules: body overrides query parameter
    api_key = query_api_key
    if request_body and request_body.api_key is not None:
        api_key = request_body.api_key

    if api_key is None:
        return None

    # Basic type and sanitization checks
    if not isinstance(api_key, str):
        raise HTTPException(status_code=400, detail="Invalid API key: must be a string")

    api_key = api_key.strip()
    if not api_key:
        return None

    # Fast fail format validation before touching external services
    # This provides better error messages and prevents unnecessary API calls
    format_errors = SettingsValidator.validate_gemini_api_key(api_key)
    if format_errors:
        # Return the first validation error as it's most descriptive
        error_detail = f"Invalid API key format: {format_errors[0]}"
        raise HTTPException(status_code=400, detail=error_detail)

    return api_key


@router.post("/models", response_model=GeminiModelsResponse)
async def get_gemini_models(
    api_key: str | None = None,
    request_body: AIRequest | None = Body(None),
) -> GeminiModelsResponse:
    """Fetch available Gemini models using configured API key from settings.

    This endpoint fetches the list of available Gemini models from Google's AI API
    using the securely stored API key from backend settings.

    Returns:
        GeminiModelsResponse with available models or error information

    Raises:
        HTTPException: For various error conditions with appropriate status codes
    """
    try:
        # Normalize and validate api_key (shared helper)
        api_key = _merge_and_validate_api_key(api_key, request_body)

        # Use ServiceClientCreators to create configured AI client (gets API key from settings)
        client_creators = ServiceClientCreators()
        ai_analyzer = client_creators.create_configured_ai_client(api_key=api_key)

        # Get the underlying GeminiClient and fetch models
        response = ai_analyzer.client.get_available_models()

        # Return appropriate HTTP status based on success
        if not response.success:
            # Combine message and error_details for comprehensive error checking
            combined_error = f"{response.message or ''} {response.error_details or ''}".lower().strip()
            error_detail = response.error_details or response.message or "Unknown error"

            if combined_error:
                # Classify error using helper function
                status_code = classify_error_status_code(combined_error)
                if status_code:
                    raise HTTPException(status_code=status_code, detail=error_detail)

            # Unknown upstream failures - use 502 Bad Gateway instead of 500
            raise HTTPException(status_code=502, detail=error_detail)

        return response

    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except ValueError as e:
        # Handle ServiceConfig validation errors (no API key configured)
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        # Handle connection-related errors (invalid API key, network issues)
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        # Handle any unexpected errors - log details but return generic message
        logger.error("Unexpected error in get_gemini_models: %s", type(e).__name__, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error occurred while fetching models")


@router.post("/models/validate-key", response_model=KeyValidationResponse)
async def validate_gemini_api_key(
    api_key: str | None = None,
    request_body: AIRequest | None = Body(None),
) -> KeyValidationResponse:
    """Validate the configured Gemini API key without fetching models.

    This endpoint provides a lightweight way to validate the API key stored
    in backend settings without the overhead of fetching the full models list.

    Returns:
        KeyValidationResponse with validation result and connection test information
    """
    try:
        api_key = _merge_and_validate_api_key(api_key, request_body)

        # Follow the endpoint pattern: use ServiceClientCreators with create_configured_*
        client_creators = ServiceClientCreators()
        client_creators.create_configured_ai_client(api_key=api_key)

        # If we get here, the client was created successfully, which means the API key is valid
        return KeyValidationResponse(
            valid=True,
            message="API key is valid and connection successful",
        )

    except HTTPException:
        raise
    except ValueError as e:
        # Handle ServiceConfig validation errors (no API key configured)
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        # Handle connection-related errors (invalid API key, network issues)
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        # Handle any unexpected errors - log details but return generic message
        logger.error("Unexpected error in validate_gemini_api_key: %s", type(e).__name__)
        raise HTTPException(status_code=500, detail="Internal server error occurred during API key validation")

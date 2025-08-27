"""AI models endpoints for TestInsight AI."""

import logging
import re
from typing import Union

from fastapi import APIRouter, HTTPException, Body

from backend.models.schemas import GeminiModelsResponse, AIRequest, KeyValidationResponse
from backend.services.service_config.client_creators import ServiceClientCreators
from backend.services.security_utils import SettingsValidator
from backend.api.routers.constants import (
    INVALID_API_KEY_FORMAT,
    FAILED_VALIDATE_AUTHENTICATION,
    INTERNAL_SERVER_ERROR_FETCHING_MODELS,
    BAD_GATEWAY_UPSTREAM_SERVICE_ERROR,
    INVALID_API_KEY_TYPE_ERROR,
    REQUEST_TIMEOUT_ERROR,
    SERVICE_UNAVAILABLE_ERROR,
    API_KEY_VALID_CLIENT_INITIALIZED,
    INTERNAL_SERVER_ERROR_VALIDATE_KEY,
)

router = APIRouter(prefix="/ai", tags=["ai"])
logger = logging.getLogger(__name__)

# Precompiled regex patterns for performance
REGEX_AUTH = re.compile(r"\bauth\b")
REGEX_QUOTA = re.compile(r"\bquota\b")
REGEX_RATE_LIMIT = re.compile(
    r"\brate(?:[\s\-]?limit|[\s\-]?limited|\s+too\s+high|\s+exceeded|\s+throttle)\b"
)  # Tightened for rate limiting contexts

# Error keyword mapping for API error status code classification
# Order matters: more specific errors should come first
# Mix of literal strings and precompiled Pattern objects for clarity and performance
ERROR_KEYWORD_MAPPING: dict[int, list[Union[str, re.Pattern[str]]]] = {
    401: [  # Authentication errors
        "invalid api key",
        "invalid-api-key",  # Hyphenated variant
        "authentication failed",
        "unauthorized",
        "api key",  # Generic but commonly used in error contexts
        "api-key",  # Hyphenated variant
        "api key invalid",
        "api key not found",
        "api key missing",
        "api-key-invalid",  # Hyphenated variants
        "api-key-not-found",
        "api-key-missing",
        REGEX_AUTH,  # Precompiled pattern for word boundary matching
        "credential",
        "invalid credentials",  # Common authentication error phrase
        "invalid token",
        "token expired",
        "missing key",  # Common variant
        "key invalid",  # Common authentication error phrase
        "access token",  # OAuth/API token variants
        "bearer token",  # Bearer authentication
        "authentication error",  # Direct auth error phrase
        "unauthenticated",  # Common auth failure term
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
        REGEX_QUOTA,  # Precompiled pattern for word boundary matching
        REGEX_RATE_LIMIT,  # Tightened pattern to avoid false positives on unrelated "rate" words
        "throttle",
        "quota limit",
        "rate exceeded",  # Common rate limit variant
        "request limit",  # API request limits
        "usage limit",  # Usage-based limits
        "throttled",  # Past tense throttling
        "rate limiting",  # Explicit rate limiting phrase
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

# Generic error messages for classified upstream errors to avoid leaking details
GENERIC_ERROR_MESSAGES = {
    401: "Authentication failed. Please verify your API key.",
    403: "Access denied. Please check your permissions.",
    429: "Rate limit exceeded. Please try again later.",
    400: "Invalid request. Please check your input.",
    503: "Service temporarily unavailable. Please try again later.",
    504: "Request timeout. Please try again later.",
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
            # Handle precompiled Pattern objects
            if isinstance(keyword, re.Pattern):
                if keyword.search(error_lower):
                    return status_code
            # Handle regular substring matching for string literals
            elif isinstance(keyword, str) and keyword in error_lower:
                return status_code

    return None


def _merge_and_validate_api_key(query_api_key: str | None, request_body: AIRequest | None) -> str | None:
    """Merge and validate API key from query parameter and request body.

    API Key Precedence (intentional design):
    1. Query parameter (?api_key=...) is used as default
    2. Request body api_key field overrides query parameter only when non-empty
    This follows REST API conventions where body parameters have higher precedence,
    but prevents empty body values from discarding valid query parameters.

    Args:
        query_api_key: API key from query parameter
        request_body: Request body containing optional API key

    Returns:
        Validated API key or None

    Raises:
        HTTPException: If API key format is invalid (400 status)
    """
    # Apply precedence rules: body overrides query parameter only when non-empty
    api_key = query_api_key
    if request_body and request_body.api_key is not None:
        # Validate type before str() coercion to prevent non-strings from overriding valid query parameters
        if not isinstance(request_body.api_key, str):
            raise HTTPException(status_code=400, detail=INVALID_API_KEY_TYPE_ERROR)

        # Check for whitespace-padded or whitespace-only API keys in body before using them
        # Empty string is handled later, but whitespace-only strings should be rejected
        if request_body.api_key and (
            request_body.api_key.strip() != request_body.api_key or request_body.api_key.strip() == ""
        ):
            raise HTTPException(status_code=400, detail=FAILED_VALIDATE_AUTHENTICATION)

        # Only override if body api_key is non-empty after trimming
        body_api_key = request_body.api_key.strip()
        if body_api_key:
            api_key = body_api_key

    if api_key is None:
        return None

    # Check for whitespace-padded or whitespace-only API keys
    if api_key.strip() != api_key or api_key.strip() == "":
        raise HTTPException(status_code=400, detail=FAILED_VALIDATE_AUTHENTICATION)

    # Basic sanitization checks (type already validated above)
    api_key = api_key.strip()

    # Fast fail format validation before touching external services
    # This provides better error messages and prevents unnecessary API calls
    format_errors = SettingsValidator.validate_gemini_api_key(api_key)
    if format_errors:
        # Return the first validation error as it's most descriptive
        error_detail = f"{INVALID_API_KEY_FORMAT}: {format_errors[0]}"
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

            if combined_error:
                # Classify error using helper function
                status_code = classify_error_status_code(combined_error)
                if status_code:
                    # Use generic message for classified errors to avoid leaking details
                    generic_detail = GENERIC_ERROR_MESSAGES.get(status_code, "An error occurred")
                    raise HTTPException(status_code=status_code, detail=generic_detail)

            # Unknown upstream failures - use 502 Bad Gateway instead of 500
            raise HTTPException(status_code=502, detail=BAD_GATEWAY_UPSTREAM_SERVICE_ERROR)

        return response

    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except ValueError as e:
        # Handle ServiceConfig validation errors (no API key configured)
        raise HTTPException(status_code=400, detail=str(e))
    except TypeError:
        # Handle invalid API key type (same as validate-key endpoint)
        logger.error("TypeError in get_gemini_models - invalid API key type")
        raise HTTPException(status_code=400, detail=INVALID_API_KEY_FORMAT)
    except TimeoutError:
        # Map timeouts to 504 Gateway Timeout
        logger.error("Timeout error in get_gemini_models - request exceeded time limit")
        raise HTTPException(status_code=504, detail=REQUEST_TIMEOUT_ERROR)
    except ConnectionError:
        # Map generic connection issues to 503 Service Unavailable
        logger.error("Connection error in get_gemini_models - service connectivity issue")
        raise HTTPException(status_code=503, detail=SERVICE_UNAVAILABLE_ERROR)
    except Exception:
        # Handle any unexpected errors - log details but return generic message
        logger.error("Unexpected error in get_gemini_models - unhandled exception occurred", exc_info=True)
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_FETCHING_MODELS)


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
            message=API_KEY_VALID_CLIENT_INITIALIZED,
        )

    except HTTPException:
        raise
    except ValueError as e:
        # Handle ServiceConfig validation errors (no API key configured)
        raise HTTPException(status_code=400, detail=str(e))
    except TypeError:
        # Handle invalid API key type (same as models endpoint)
        logger.error("TypeError in validate_gemini_api_key - invalid API key type")
        raise HTTPException(status_code=400, detail=INVALID_API_KEY_FORMAT)
    except TimeoutError:
        # Map timeouts to 504 Gateway Timeout
        logger.error("Timeout error in validate_gemini_api_key - request exceeded time limit")
        raise HTTPException(status_code=504, detail=REQUEST_TIMEOUT_ERROR)
    except ConnectionError:
        # Map generic connection issues to 503 Service Unavailable
        logger.error("Connection error in validate_gemini_api_key - service connectivity issue")
        raise HTTPException(status_code=503, detail=SERVICE_UNAVAILABLE_ERROR)
    except Exception:
        # Handle any unexpected errors - log details but return generic message
        logger.error("Unexpected error in validate_gemini_api_key - unhandled exception occurred", exc_info=True)
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_VALIDATE_KEY)

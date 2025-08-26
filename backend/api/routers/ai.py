"""AI models endpoints for TestInsight AI."""

import logging

from fastapi import APIRouter, HTTPException, Body

from backend.models.schemas import GeminiModelsResponse, AIRequest
from backend.services.service_config.client_creators import ServiceClientCreators

router = APIRouter(prefix="/ai", tags=["ai"])
logger = logging.getLogger(__name__)


def _merge_and_validate_api_key(query_api_key: str | None, request_body: AIRequest | None) -> str | None:
    """Merge and validate API key from query parameter and request body.

    Args:
        query_api_key: API key from query parameter
        request_body: Request body containing optional API key

    Returns:
        Validated API key or None

    Raises:
        HTTPException: If API key is invalid
    """
    api_key = query_api_key
    if request_body and request_body.api_key is not None:
        api_key = request_body.api_key

    if api_key is None:
        return None

    if not isinstance(api_key, str):
        raise HTTPException(status_code=400, detail="Invalid API key: must be a string")

    api_key = api_key.strip()
    if not api_key:
        return None
    if len(api_key) < 10:
        raise HTTPException(status_code=400, detail="Invalid API key: too short")
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
                # Authentication errors (401)
                if any(
                    term in combined_error
                    for term in [
                        "invalid api key",
                        "authentication failed",
                        "unauthorized",
                        "api key",
                        "auth",
                        "credential",
                        "invalid token",
                        "token expired",
                    ]
                ):
                    raise HTTPException(status_code=401, detail=error_detail)

                # Permission/access errors (403)
                elif any(
                    term in combined_error
                    for term in [
                        "permission denied",
                        "access denied",
                        "forbidden",
                        "not allowed",
                        "insufficient permissions",
                    ]
                ):
                    raise HTTPException(status_code=403, detail=error_detail)

                # Rate limiting/quota errors (429)
                elif any(
                    term in combined_error
                    for term in [
                        "quota exceeded",
                        "rate limit",
                        "too many requests",
                        "quota",
                        "rate",
                        "throttle",
                        "quota limit",
                    ]
                ):
                    raise HTTPException(status_code=429, detail=error_detail)

                # Bad request errors (400)
                elif any(
                    term in combined_error
                    for term in [
                        "invalid input",
                        "bad request",
                        "malformed",
                        "invalid request",
                        "validation error",
                        "invalid parameter",
                    ]
                ):
                    raise HTTPException(status_code=400, detail=error_detail)

                # Service unavailable errors (503)
                elif any(
                    term in combined_error
                    for term in [
                        "service unavailable",
                        "temporarily unavailable",
                        "maintenance",
                        "overloaded",
                        "server busy",
                    ]
                ):
                    raise HTTPException(status_code=503, detail=error_detail)

                # Timeout errors (504)
                elif any(term in combined_error for term in ["timeout", "timed out", "deadline exceeded"]):
                    raise HTTPException(status_code=504, detail=error_detail)

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
        logger.error("Unexpected error in get_gemini_models: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error occurred while fetching models")


@router.post("/models/validate-key")
async def validate_gemini_api_key(
    api_key: str | None = None,
    request_body: AIRequest | None = Body(None),
) -> dict[str, bool | str]:
    """Validate the configured Gemini API key without fetching models.

    This endpoint provides a lightweight way to validate the API key stored
    in backend settings without the overhead of fetching the full models list.

    Returns:
        Dictionary with validation result and connection test information
    """
    try:
        api_key = _merge_and_validate_api_key(api_key, request_body)

        # Follow the endpoint pattern: use ServiceClientCreators with create_configured_*
        client_creators = ServiceClientCreators()
        client_creators.create_configured_ai_client(api_key=api_key)

        # If we get here, the client was created successfully, which means the API key is valid
        return {
            "valid": True,
            "message": "API key is valid and connection successful",
        }

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
        logger.error("Unexpected error in validate_gemini_api_key: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error occurred during API key validation")

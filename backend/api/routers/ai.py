"""AI models endpoints for TestInsight AI."""

from typing import Any

from fastapi import APIRouter, HTTPException, Body

from backend.models.schemas import GeminiModelsResponse
from backend.services.service_config.client_creators import ServiceClientCreators

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/models", response_model=GeminiModelsResponse)
async def get_gemini_models(
    api_key: str | None = None,
    payload: dict[str, Any] | None = Body(None),
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
        # Prefer JSON body api_key when provided
        if payload and isinstance(payload, dict) and "api_key" in payload and not api_key:
            api_key = payload.get("api_key")

        # Validate and normalize api_key early to avoid TypeError/500s
        if api_key is not None:
            # Ensure api_key is a string, reject non-string types with 400
            if not isinstance(api_key, str):
                raise HTTPException(status_code=400, detail="Invalid API key: must be a string")

            # Trim whitespace and treat empty strings as missing
            api_key = api_key.strip()
            if not api_key:  # Empty string after stripping
                api_key = None
            elif len(api_key) < 10:  # Quick validation for explicit short keys (test expects 400)
                raise HTTPException(status_code=400, detail="Invalid API key: too short")

        # Use ServiceClientCreators to create configured AI client (gets API key from settings)
        client_creators = ServiceClientCreators()
        ai_analyzer = client_creators.create_configured_ai_client(api_key=api_key)

        # Get the underlying GeminiClient and fetch models
        response = ai_analyzer.client.get_available_models()

        # Return appropriate HTTP status based on success
        if not response.success:
            if response.error_details and response.message:
                # Determine appropriate HTTP status code based on error type
                if "Invalid API key" in response.error_details or "Authentication failed" in response.message:
                    raise HTTPException(status_code=401, detail=response.error_details or response.message)
                elif "Permission denied" in response.message:
                    raise HTTPException(status_code=403, detail=response.error_details or response.message)
                elif "quota exceeded" in response.message.lower():
                    raise HTTPException(status_code=429, detail=response.error_details or response.message)
                elif "Invalid input" in response.message:
                    raise HTTPException(status_code=400, detail=response.error_details or response.message)
            else:
                # Generic server error for other cases
                raise HTTPException(status_code=500, detail=response.error_details or response.message)

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
        # Handle any unexpected errors
        raise HTTPException(status_code=500, detail=f"Failed to fetch Gemini models: {str(e)}")


@router.post("/models/validate-key")
async def validate_gemini_api_key(api_key: str | None) -> dict[str, Any]:
    """Validate the configured Gemini API key without fetching models.

    This endpoint provides a lightweight way to validate the API key stored
    in backend settings without the overhead of fetching the full models list.

    Returns:
        Dictionary with validation result and connection test information
    """
    try:
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
        raise HTTPException(status_code=500, detail=f"API key validation failed: {str(e)}")

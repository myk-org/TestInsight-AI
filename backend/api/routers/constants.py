"""
Constants for API router error messages and responses.
"""

# Error message constants for consistent messaging across endpoints
INVALID_API_KEY_FORMAT = "Invalid API key format"  # pragma: allowlist secret
FAILED_VALIDATE_AUTHENTICATION = "Failed to validate authentication"
INTERNAL_SERVER_ERROR_FETCHING_MODELS = "Internal server error occurred while fetching models"
BAD_GATEWAY_UPSTREAM_SERVICE_ERROR = "Bad gateway - upstream service error"
INVALID_API_KEY_TYPE_ERROR = "Invalid API key: must be a string"  # pragma: allowlist secret
REQUEST_TIMEOUT_ERROR = "Request timeout"
SERVICE_UNAVAILABLE_ERROR = "Service unavailable"
API_KEY_VALID_CLIENT_INITIALIZED = (
    "API key format is valid and client initialized successfully"  # pragma: allowlist secret
)
INTERNAL_SERVER_ERROR_VALIDATE_KEY = (
    "Internal server error occurred during API key validation"  # pragma: allowlist secret
)

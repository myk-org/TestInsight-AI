"""FastAPI application for TestInsight AI."""

import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable, Awaitable

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi import HTTPException as FastAPIHTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from backend.api.main import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Load environment variables
    load_dotenv()

    # Configure logging
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO))
    logger = logging.getLogger("testinsight")

    # Configure CORS after environment is loaded
    setup_cors_middleware(app)

    # Startup
    logger.info("TestInsight AI starting up…")

    yield

    # Shutdown
    logger.info("TestInsight AI shutting down…")


# Load environment variables early to avoid config drift
load_dotenv()

app = FastAPI(
    title="TestInsight AI",
    description="AI-powered test analysis and insights platform",
    version=os.getenv("APP_VERSION", "0.1.0"),
    lifespan=lifespan,
)


def normalize_cors_origins(origins_str: str) -> list[str]:
    """
    Parse, deduplicate, and normalize CORS origins while preserving order.
    Short-circuits for wildcard origins to maintain security semantics.

    Args:
        origins_str: Comma-separated origins string

    Returns:
        List of normalized, deduplicated origins
    """
    if not origins_str:
        return ["*"]

    origins = [o.strip() for o in origins_str.split(",") if o.strip()]
    if not origins:
        return ["*"]

    # SECURITY: Short-circuit for wildcard origin to maintain proper semantics
    for origin in origins:
        if origin.strip() == "*":
            return ["*"]

    # Deduplicate while preserving order
    seen = set()
    normalized_origins = []
    for origin in origins:
        # Normalize by removing trailing slashes
        normalized = origin.rstrip("/")
        if normalized not in seen:
            seen.add(normalized)
            normalized_origins.append(normalized)

    return normalized_origins


def parse_boolean_env(env_value: str | None, default: bool = False) -> bool:
    """
    Parse boolean environment variable with support for various truthy values.
    Properly handles whitespace and honors default for unrecognized tokens.

    Args:
        env_value: Environment variable value (can be None)
        default: Default value if env_value is None, empty, or unrecognized

    Returns:
        Parsed boolean value
    """
    if not env_value:
        return default

    # Strip whitespace and handle empty after stripping
    cleaned_value = env_value.strip()
    if not cleaned_value:
        return default

    # Support various truthy values: true, yes, 1, on
    if cleaned_value.lower() in ("true", "yes", "1", "on"):
        return True

    # Support various falsy values: false, no, 0, off
    if cleaned_value.lower() in ("false", "no", "0", "off"):
        return False

    # Return default for unrecognized tokens
    return default


def setup_cors_middleware(app: FastAPI) -> None:
    """
    Configure CORS middleware with proper security checks.
    Called during lifespan startup after environment is loaded.
    """
    # Default to localhost origins for development (including HTTPS) to support credentials
    default_origins = "http://localhost:3000,http://127.0.0.1:3000,https://localhost:3000,https://127.0.0.1:3000"
    cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", default_origins)

    allow_origins = normalize_cors_origins(cors_origins_env)
    allow_credentials_env = os.getenv("CORS_ALLOW_CREDENTIALS", "true")
    allow_credentials = parse_boolean_env(allow_credentials_env, True)

    # SECURITY: Wildcard origins cannot use credentials - detect ANY wildcard presence
    if "*" in allow_origins and allow_credentials:
        logging.getLogger("testinsight").warning(
            "CORS credentials disabled due to wildcard origin (*). Specify explicit origins to enable credentials."
        )
        allow_credentials = False

    # Register CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Optional global error handler (env gated) while preserving default FastAPI behavior otherwise
if os.getenv("ENABLE_GLOBAL_ERROR_HANDLER", "false").lower() == "true":

    async def error_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        try:
            return await call_next(request)
        except FastAPIHTTPException:
            # Preserve intended HTTP semantics for client errors
            raise
        except Exception:  # pragma: no cover (covered indirectly via API tests)
            # Log and return consistent JSON envelope
            logging.getLogger("testinsight").exception("Unhandled error")
            return JSONResponse(
                status_code=500,
                content={"error": {"code": 500, "message": "Internal Server Error"}},
            )

    app.add_middleware(BaseHTTPMiddleware, dispatch=error_middleware)


# Security headers middleware (always on, without external dependency)
@app.middleware("http")
async def security_headers(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


# Include API routes
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Welcome to TestInsight AI"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )

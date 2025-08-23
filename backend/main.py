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
from starlette.responses import JSONResponse
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

    # Startup
    logger.info("TestInsight AI starting up…")

    yield

    # Shutdown
    logger.info("TestInsight AI shutting down…")


app = FastAPI(
    title="TestInsight AI",
    description="AI-powered test analysis and insights platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS via environment-driven allowlist
cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "*")
allow_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()] if cors_origins_env else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Optional global error handler (env gated) while preserving default FastAPI behavior otherwise
if os.getenv("ENABLE_GLOBAL_ERROR_HANDLER", "false").lower() == "true":

    async def error_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[JSONResponse]]
    ) -> JSONResponse:
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
async def security_headers(request: Request, call_next: Callable[[Request], Awaitable[JSONResponse]]) -> JSONResponse:
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

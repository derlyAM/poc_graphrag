"""
FastAPI middleware configuration.
CORS, logging, and request tracking.
"""
import time
from typing import Callable
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import uuid


def add_cors_middleware(app) -> None:
    """
    Add CORS middleware to FastAPI app.

    Args:
        app: FastAPI application instance
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:8501",  # Streamlit
            "http://localhost:8000",  # API itself
            "*"  # Allow all origins (adjust for production)
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("CORS middleware configured")


async def log_requests_middleware(
    request: Request,
    call_next: Callable
) -> Response:
    """
    Middleware to log all requests and responses.

    Args:
        request: FastAPI request
        call_next: Next middleware/route handler

    Returns:
        Response from route handler
    """
    # Generate request ID
    request_id = str(uuid.uuid4())[:8]

    # Log request
    logger.info(
        f"[{request_id}] {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )

    # Time the request
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Log response
    logger.info(
        f"[{request_id}] Completed in {duration:.3f}s "
        f"with status {response.status_code}"
    )

    # Add custom headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{duration:.3f}"

    return response


def setup_middleware(app) -> None:
    """
    Setup all middleware for the FastAPI app.

    Args:
        app: FastAPI application instance
    """
    add_cors_middleware(app)
    app.middleware("http")(log_requests_middleware)
    logger.info("All middleware configured")

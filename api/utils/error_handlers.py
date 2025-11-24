"""
Error handlers for FastAPI application.
Custom exception handlers for graceful error responses.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handle validation errors from Pydantic models.

    Args:
        request: FastAPI request object
        exc: Validation exception

    Returns:
        JSONResponse with error details
    """
    errors = exc.errors()
    logger.warning(f"Validation error: {errors}")

    # Format validation errors for user-friendly response
    error_messages = []
    for error in errors:
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        error_messages.append(f"{field}: {message}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "Validation error",
            "error_code": "VALIDATION_ERROR",
            "details": {
                "errors": error_messages,
                "raw_errors": errors
            }
        }
    )


async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle general exceptions.

    Args:
        request: FastAPI request object
        exc: Exception

    Returns:
        JSONResponse with error details
    """
    logger.error(f"Unhandled exception: {exc}")
    logger.exception("Full traceback:")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": f"Internal server error: {str(exc)}",
            "error_code": "INTERNAL_ERROR",
        }
    )

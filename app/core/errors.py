"""
Error Handling

Standardized error responses and exception handlers.
"""

from typing import Any
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from app.core.logging import get_logger

logger = get_logger(__name__)


class ErrorResponse(BaseModel):
    """Standardized error response format"""
    error: str
    code: str
    details: dict[str, Any] = {}


class AppException(Exception):
    """Base application exception"""
    def __init__(
        self,
        error: str,
        code: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] = None
    ):
        self.error = error
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(error)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    errors = exc.errors()
    
    logger.warning(
        f"Validation failed: {len(errors)} error(s)",
        extra={
            "path": request.url.path,
            "errors": errors,
            "request_id": getattr(request.state, "request_id", None)
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation failed",
            "code": "VALIDATION_ERROR",
            "details": {
                "errors": [
                    {
                        "field": ".".join(str(loc) for loc in err["loc"]),
                        "message": err["msg"],
                        "type": err["type"]
                    }
                    for err in errors
                ]
            }
        }
    )


async def app_exception_handler(request: Request, exc: AppException):
    """Handle application exceptions"""
    logger.error(
        f"Application error: {exc.error}",
        extra={
            "code": exc.code,
            "path": request.url.path,
            "details": exc.details,
            "request_id": getattr(request.state, "request_id", None)
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error,
            "code": exc.code,
            "details": exc.details
        }
    )


async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(
        f"Unhandled exception: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
            "request_id": getattr(request.state, "request_id", None)
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "code": "INTERNAL_ERROR",
            "details": {"message": str(exc)}
        }
    )

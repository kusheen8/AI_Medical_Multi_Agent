"""
Global exception handlers for API v1.

Maps repository-layer exceptions to appropriate HTTP status codes
with structured error responses. Includes auth and rate limit handlers (Phase 5).
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jose import JWTError

from app.db.exceptions import DuplicateError, NotFoundError, RepositoryError


def register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI application.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "detail": exc.message,
                "errors": [
                    {
                        "resource_type": exc.resource_type,
                        "resource_id": exc.resource_id,
                    }
                ],
            },
        )

    @app.exception_handler(DuplicateError)
    async def duplicate_handler(request: Request, exc: DuplicateError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "detail": exc.message,
                "errors": [],
            },
        )

    @app.exception_handler(RepositoryError)
    async def repository_error_handler(request: Request, exc: RepositoryError) -> JSONResponse:
        # Suppress internal details — never leak DB info
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal error occurred.",
                "errors": [],
            },
        )

    @app.exception_handler(JWTError)
    async def jwt_error_handler(request: Request, exc: JWTError) -> JSONResponse:
        """Handle JWT validation errors globally."""
        return JSONResponse(
            status_code=401,
            content={
                "detail": "Invalid or expired authentication token.",
                "errors": [],
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = []
        for error in exc.errors():
            errors.append(
                {
                    "field": " → ".join(str(loc) for loc in error.get("loc", [])),
                    "message": error.get("msg", ""),
                    "type": error.get("type", ""),
                }
            )
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Validation error: one or more fields failed validation.",
                "errors": errors,
            },
        )

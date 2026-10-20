import traceback
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError, NoResultFound

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config.logging import get_logger
from app.llm.base import (
    LLMError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMAuthenticationError,
)

logger = get_logger(__name__)


def add_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.warning(
            "http_exception",
            path=request.url.path,
            status_code=exc.status_code,
            detail=exc.detail,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "status_code": exc.status_code},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(
            "validation_error",
            path=request.url.path,
            errors=exc.errors(),
        )
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "status_code": 422},
        )

    @app.exception_handler(LLMError)
    async def llm_error_handler(request: Request, exc: LLMError):
        if isinstance(exc, LLMRateLimitError):
            status_code = 429
            detail = "LLM rate limit exceeded. Please try again later."
        elif isinstance(exc, LLMTimeoutError):
            status_code = 504
            detail = "LLM request timed out. Please try again."
        elif isinstance(exc, LLMAuthenticationError):
            status_code = 401
            detail = "LLM authentication failed. Please check configuration."
        elif isinstance(exc, LLMProviderError):
            status_code = 502
            detail = f"LLM provider error: {exc.provider}"
        else:
            status_code = 500
            detail = "LLM service error"
        
        logger.warning(
            "llm_error",
            path=request.url.path,
            error_type=type(exc).__name__,
            detail=str(exc),
        )
        return JSONResponse(
            status_code=status_code,
            content={"detail": detail, "status_code": status_code, "error_type": type(exc).__name__},
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
        if isinstance(exc, IntegrityError):
            status_code = 409
            detail = "Database integrity constraint violation"
        elif isinstance(exc, OperationalError):
            status_code = 503
            detail = "Database connection error. Please try again later."
        elif isinstance(exc, NoResultFound):
            status_code = 404
            detail = "Resource not found"
        else:
            status_code = 500
            detail = "Database error"
        
        logger.error(
            "database_error",
            path=request.url.path,
            error_type=type(exc).__name__,
            detail=str(exc),
            traceback=traceback.format_exc(),
        )
        return JSONResponse(
            status_code=status_code,
            content={"detail": detail, "status_code": status_code, "error_type": type(exc).__name__},
        )

    @app.exception_handler(FileNotFoundError)
    async def file_not_found_handler(request: Request, exc: FileNotFoundError):
        logger.warning(
            "file_not_found",
            path=request.url.path,
            detail=str(exc),
        )
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc), "status_code": 404},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        logger.warning(
            "value_error",
            path=request.url.path,
            detail=str(exc),
        )
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "status_code": 400},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "status_code": 500},
        )

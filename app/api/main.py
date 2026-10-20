from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware.error_handler import add_error_handlers
from app.api.middleware.logging import LoggingMiddleware
from app.api.routes import (
    analysis,
    companies,
    comparison,
    dashboard,
    documents,
    explainability,
    financial_health,
    health,
    industry_intelligence,
    market_intelligence,
    reports,
    risk_explorer,
    risks,
    scanner,
)
from app.config.logging import get_logger, setup_logging
from app.config.settings import get_settings
from app.db.session import close_db, init_db

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    logger.info("application_starting")

    await init_db()
    logger.info("database_initialized")

    yield

    await close_db()
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Corporate Risk Intelligence Platform API",
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(LoggingMiddleware)
    add_error_handlers(app)

    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
    app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["analysis"])
    app.include_router(companies.router, prefix="/api/v1/companies", tags=["companies"])
    app.include_router(risks.router, prefix="/api/v1/risks", tags=["risks"])
    app.include_router(comparison.router, prefix="/api/v1/comparison", tags=["comparison"])
    app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
    app.include_router(
        explainability.router,
        prefix="/api/v1/explainability",
        tags=["explainability"],
    )
    app.include_router(
        financial_health.router,
        prefix="/api/v1/financial-health",
        tags=["financial-health"],
    )
    app.include_router(
        market_intelligence.router,
        prefix="/api/v1/market-intelligence",
        tags=["market-intelligence"],
    )
    app.include_router(
        industry_intelligence.router,
        prefix="/api/v1/industry-intelligence",
        tags=["industry-intelligence"],
    )
    app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
    app.include_router(
        risk_explorer.router,
        prefix="/api/v1/risk-explorer",
        tags=["risk-explorer"],
    )
    app.include_router(scanner.router, prefix="/api/v1/scanner", tags=["scanner"])

    # Add test error routes when running tests
    if os.getenv("PYTEST_CURRENT_TEST") or os.getenv("TESTING"):
        from app.llm.base import (
            LLMRateLimitError,
            LLMTimeoutError,
            LLMAuthenticationError,
            LLMProviderError,
        )
        from sqlalchemy.exc import IntegrityError
        from fastapi import APIRouter

        test_error_router = APIRouter(prefix="/test-errors", tags=["test-errors"])

        @test_error_router.get("/llm-rate-limit")
        async def test_llm_rate_limit():
            raise LLMRateLimitError("Rate limit exceeded")

        @test_error_router.get("/llm-timeout")
        async def test_llm_timeout():
            raise LLMTimeoutError("Request timed out")

        @test_error_router.get("/llm-auth")
        async def test_llm_auth():
            raise LLMAuthenticationError("Invalid API key")

        @test_error_router.get("/llm-provider")
        async def test_llm_provider():
            raise LLMProviderError("groq", "Service unavailable")

        @test_error_router.get("/value-error")
        async def test_value_error():
            raise ValueError("Invalid criteria: year_current must be greater than year_previous")

        @test_error_router.get("/file-not-found")
        async def test_file_not_found():
            raise FileNotFoundError("PDF file not found: test.pdf")

        @test_error_router.get("/runtime-error")
        async def test_runtime_error():
            raise RuntimeError("Unexpected error")

        @test_error_router.post("/integrity-error")
        async def test_integrity_error():
            raise IntegrityError("duplicate key", "params", "orig")

        app.include_router(test_error_router)

    return app


app = create_app()

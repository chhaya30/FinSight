from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware.error_handler import add_error_handlers
from app.api.middleware.logging import LoggingMiddleware
from app.api.routes import analysis, companies, comparison, documents, health, reports, risks
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
    app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])

    return app


app = create_app()

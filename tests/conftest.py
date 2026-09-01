import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.main import app
from app.db.base import Base
from app.db.session import get_db_session
from app.config.settings import get_settings


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def sample_company_data():
    return {
        "name": "Test Company Ltd",
        "sector": "Technology",
        "market_cap": 1000000.0,
        "listed_exchange": "NSE",
    }


@pytest.fixture
def sample_report_data():
    return {
        "company_id": "test-uuid",
        "fiscal_year": 2024,
        "source_file": "test.pdf",
        "source_file_hash": "abc123",
        "file_size_bytes": 1024000,
    }


@pytest.fixture
def sample_risk_data():
    return {
        "report_id": "test-uuid",
        "category": "cyber",
        "severity": "high",
        "confidence_score": 0.9,
        "summary": "Cybersecurity risk detected",
        "source_page": 5,
        "source_paragraph": "The company faces significant cybersecurity risks...",
    }
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes._phase2_helpers import load_phase2_records
from app.db.base import Company, Report, RiskItem
from app.db.session import get_db_session
from app.config.settings import get_settings
from app.intelligence.external_providers import GdeltMarketProvider
from app.intelligence.market import (
    MarketIntelligenceProvider,
    MarketIntelligenceService,
    NullMarketProvider,
)
from app.models.market_intelligence import MarketIntelligenceResponse

router = APIRouter()


def get_market_provider() -> MarketIntelligenceProvider:
    settings = get_settings()
    if settings.MARKET_INTELLIGENCE_PROVIDER.casefold() == "gdelt":
        return GdeltMarketProvider()
    return NullMarketProvider()


@router.get("/{company_id}/events", response_model=MarketIntelligenceResponse)
async def get_market_intelligence(
    company_id: UUID,
    year_current: int | None = Query(None, ge=1900, le=2100),
    year_previous: int | None = Query(None, ge=1900, le=2100),
    db: AsyncSession = Depends(get_db_session),
    provider: MarketIntelligenceProvider = Depends(get_market_provider),
) -> MarketIntelligenceResponse:
    company = await db.get(Company, company_id)
    if not company:
        return MarketIntelligenceResponse(
            company_id=company_id,
            company_name="Unknown company",
            provider=provider.name,
            provider_available=provider.is_available(),
            error="Company not found",
        )
    records = []
    reports_result = await db.execute(
        select(Report).where(Report.company_id == company_id).order_by(Report.fiscal_year)
    )
    reports = list(reports_result.scalars().all())
    current = next((item for item in reports if item.fiscal_year == year_current), None) if year_current else (reports[-1] if reports else None)
    previous = next((item for item in reports if item.fiscal_year == year_previous), None) if year_previous else None
    if previous is None and current is not None:
        previous = next((item for item in reversed(reports) if item.fiscal_year < current.fiscal_year), None)
    if previous and current and previous.fiscal_year < current.fiscal_year:
        previous_result = await db.execute(
            select(RiskItem).where(RiskItem.report_id == previous.id)
        )
        current_result = await db.execute(
            select(RiskItem).where(RiskItem.report_id == current.id)
        )
        records, _, _ = await load_phase2_records(
            previous,
            current,
            previous_result.scalars().all(),
            current_result.scalars().all(),
        )
    return await MarketIntelligenceService(provider).fetch_for_company(
        str(company.id), company.name, records
    )

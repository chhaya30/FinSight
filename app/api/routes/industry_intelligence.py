from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes._phase2_helpers import load_phase2_records
from app.db.base import Company, Report, RiskItem
from app.db.session import get_db_session
from app.config.settings import get_settings
from app.intelligence.external_providers import SecEdgarIndustryProvider
from app.intelligence.industry import (
    IndustryIntelligenceProvider,
    IndustryIntelligenceService,
    NullIndustryProvider,
)
from app.models.industry_intelligence import IndustryIntelligenceResponse

router = APIRouter()


def get_industry_provider() -> IndustryIntelligenceProvider:
    settings = get_settings()
    if settings.INDUSTRY_INTELLIGENCE_PROVIDER.casefold() == "sec_edgar":
        return SecEdgarIndustryProvider()
    return NullIndustryProvider()


@router.get("/{company_id}", response_model=IndustryIntelligenceResponse)
async def get_industry_intelligence(
    company_id: UUID,
    year: int | None = Query(None, ge=1900, le=2100),
    year_previous: int | None = Query(None, ge=1900, le=2100),
    industry: str | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
    provider: IndustryIntelligenceProvider = Depends(get_industry_provider),
) -> IndustryIntelligenceResponse:
    company = await db.get(Company, str(company_id))
    if not company:
        return IndustryIntelligenceResponse(
            company_id=company_id,
            company_name="Unknown company",
            industry=industry,
            provider=provider.name,
            provider_available=provider.is_available(),
            error="Company not found",
        )
    risk_records = []
    reports_result = await db.execute(
        select(Report).where(Report.company_id == company_id).order_by(Report.fiscal_year)
    )
    reports = list(reports_result.scalars().all())
    current = next((item for item in reports if item.fiscal_year == year), None) if year else (reports[-1] if reports else None)
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
        risk_records, _, _ = await load_phase2_records(
            previous,
            current,
            previous_result.scalars().all(),
            current_result.scalars().all(),
            session=db,
        )
    return await IndustryIntelligenceService(provider).analyze_company(
        str(company.id), company.name, industry or company.sector, risk_records
    )

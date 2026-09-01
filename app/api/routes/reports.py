from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config.logging import get_logger
from app.db.base import Company, FinancialSnapshot, Report, RiskItem
from app.db.session import get_db_session
from app.models.intelligence import (
    ExecutiveSummaryRequest,
    ExecutiveSummaryResponse,
    FinancialHealthResponse,
    PeerComparisonRequest,
    PeerComparisonResponse,
)

logger = get_logger(__name__)

router = APIRouter()


@router.post("/executive-summary", response_model=ExecutiveSummaryResponse)
async def generate_executive_summary(
    request: ExecutiveSummaryRequest,
    db: AsyncSession = Depends(get_db_session),
):
    company = await db.get(Company, request.company_id, options=[selectinload(Company.reports)])
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    target_year = request.year
    if target_year is None:
        target_year = max((r.fiscal_year for r in company.reports), default=None)

    if target_year is None:
        raise HTTPException(status_code=404, detail="No reports found for company")

    report = next((r for r in company.reports if r.fiscal_year == target_year), None)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report for FY{target_year} not found")

    risks = await db.execute(select(RiskItem).where(RiskItem.report_id == report.id))
    risks = risks.scalars().all()

    risk_distribution = {}
    for risk in risks:
        risk_distribution[risk.severity] = risk_distribution.get(risk.severity, 0) + 1

    top_risks = sorted(risks, key=lambda r: r.confidence_score, reverse=True)[:5]

    financial = await db.execute(
        select(FinancialSnapshot).where(
            FinancialSnapshot.company_id == request.company_id,
            FinancialSnapshot.fiscal_year == target_year,
        )
    )
    financial = financial.scalar_one_or_none()

    return ExecutiveSummaryResponse(
        company_id=request.company_id,
        company_name=company.name,
        fiscal_year=target_year,
        overall_risk_score=sum(r.confidence_score for r in risks) / len(risks) if risks else 0,
        risk_distribution=risk_distribution,
        top_risks=[
            {
                "category": r.category,
                "severity": r.severity,
                "summary": r.summary,
                "confidence": r.confidence_score,
            }
            for r in top_risks
        ],
        key_changes=[],
        financial_health="Financial data available" if financial else "No financial data",
        ai_narrative=(
            f"Executive summary for {company.name} FY{target_year}. "
            f"{len(risks)} material risks identified across "
            f"{len(risk_distribution)} severity levels."
        ),
        confidence_score=0.85,
        generated_at=func.now(),
    )


@router.get("/{company_id}/financial-health", response_model=FinancialHealthResponse)
async def get_financial_health(
    company_id: UUID,
    fiscal_year: int | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if fiscal_year is None:
        report = await db.execute(
            select(Report)
            .where(Report.company_id == company_id)
            .order_by(Report.fiscal_year.desc())
        )
        report = report.scalar_one_or_none()
        if report:
            fiscal_year = report.fiscal_year

    if fiscal_year is None:
        raise HTTPException(status_code=404, detail="No reports found for company")

    financial = await db.execute(
        select(FinancialSnapshot).where(
            FinancialSnapshot.company_id == company_id,
            FinancialSnapshot.fiscal_year == fiscal_year,
        )
    )
    financial = financial.scalar_one_or_none()

    if not financial:
        raise HTTPException(status_code=404, detail="Financial snapshot not found")

    return FinancialHealthResponse(
        company_id=company_id,
        fiscal_year=fiscal_year,
        metrics=[],
        revenue=financial.revenue,
        profit=financial.profit,
        net_margin=financial.net_margin,
        roe=financial.roe,
        roce=financial.roce,
        eps=financial.eps,
        debt_equity=financial.debt_equity,
        cash_flow=financial.cash_flow,
        market_cap=financial.market_cap,
    )


@router.post("/peer-comparison", response_model=PeerComparisonResponse)
async def peer_comparison(
    request: PeerComparisonRequest,
    db: AsyncSession = Depends(get_db_session),
):
    company = await db.get(Company, request.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    peers_query = select(Company).where(Company.id != request.company_id)
    if request.sector:
        peers_query = peers_query.where(Company.sector == request.sector)
    if request.peer_company_ids:
        peers_query = peers_query.where(Company.id.in_(request.peer_company_ids))

    peers_result = await db.execute(peers_query.limit(10))
    peers = peers_result.scalars().all()

    return PeerComparisonResponse(
        company_id=request.company_id,
        peers=[{"id": str(p.id), "name": p.name, "sector": p.sector} for p in peers],
        benchmark_metrics={},
        risk_profile_comparison={},
        total_peers=len(peers),
    )


@router.get("/{company_id}/risk-explorer")
async def risk_explorer(
    company_id: UUID,
    category: str | None = Query(None),
    severity: str | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    query = (
        select(RiskItem)
        .join(Report, RiskItem.report_id == Report.id)
        .where(Report.company_id == company_id)
    )

    if category:
        query = query.where(RiskItem.category == category)
    if severity:
        query = query.where(RiskItem.severity == severity)

    result = await db.execute(query)
    risks = result.scalars().all()

    return {
        "company_id": company_id,
        "filters": {"category": category, "severity": severity},
        "risks_found": len(risks),
        "risks": [
            {
                "id": str(r.id),
                "category": r.category,
                "severity": r.severity,
                "summary": r.summary,
                "confidence": r.confidence_score,
                "year": r.report.fiscal_year if r.report else None,
            }
            for r in risks
        ],
    }

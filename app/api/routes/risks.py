from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config.logging import get_logger
from app.db.base import EvolutionEntry, Report, RiskItem
from app.db.session import get_db_session
from app.models.comparison import EvolutionEntryResponse
from app.models.risk import RiskItemListResponse, RiskItemResponse

logger = get_logger(__name__)

router = APIRouter()


@router.get("", response_model=RiskItemListResponse)
async def list_risks(
    company_id: UUID | None = Query(None),
    report_id: UUID | None = Query(None),
    category: str | None = Query(None),
    severity: str | None = Query(None),
    min_confidence: float | None = Query(None, ge=0, le=1),
    fiscal_year: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
):
    query = select(RiskItem).join(Report, RiskItem.report_id == Report.id)

    if company_id:
        query = query.where(Report.company_id == company_id)
    if report_id:
        query = query.where(RiskItem.report_id == report_id)
    if category:
        query = query.where(RiskItem.category == category)
    if severity:
        query = query.where(RiskItem.severity == severity)
    if min_confidence:
        query = query.where(RiskItem.confidence_score >= min_confidence)
    if fiscal_year:
        query = query.where(Report.fiscal_year == fiscal_year)

    query = query.order_by(RiskItem.confidence_score.desc())

    total_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(total_query)

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    risks = result.scalars().all()

    return RiskItemListResponse(
        risks=[RiskItemResponse.model_validate(r) for r in risks],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{risk_id}", response_model=RiskItemResponse)
async def get_risk(
    risk_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    risk = await db.get(
        RiskItem, risk_id, options=[selectinload(RiskItem.report).selectinload(Report.company)]
    )
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")

    return RiskItemResponse.model_validate(risk)


@router.get("/{risk_id}/evolution", response_model=list[EvolutionEntryResponse])
async def get_risk_evolution(
    risk_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    risk = await db.get(RiskItem, risk_id)
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")

    result = await db.execute(
        select(EvolutionEntry).where(
            (EvolutionEntry.risk_item_id_prev == risk_id)
            | (EvolutionEntry.risk_item_id_current == risk_id)
        )
    )
    evolutions = result.scalars().all()

    return [EvolutionEntryResponse.model_validate(e) for e in evolutions]


@router.get("/stats/summary")
async def get_risk_summary(
    company_id: UUID | None = Query(None),
    fiscal_year: int | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    query = select(RiskItem).join(Report, RiskItem.report_id == Report.id)

    if company_id:
        query = query.where(Report.company_id == company_id)
    if fiscal_year:
        query = query.where(Report.fiscal_year == fiscal_year)

    risks = (await db.execute(query)).scalars().all()

    total = len(risks)
    by_category = {}
    by_severity = {}
    confidence_sum = 0

    for risk in risks:
        by_category[risk.category] = by_category.get(risk.category, 0) + 1
        by_severity[risk.severity] = by_severity.get(risk.severity, 0) + 1
        confidence_sum += risk.confidence_score

    return {
        "total_risks": total,
        "by_category": by_category,
        "by_severity": by_severity,
        "avg_confidence": confidence_sum / total if total > 0 else 0,
    }


@router.get("/stats/trends")
async def get_risk_trends(
    company_id: UUID,
    years: int = Query(5, ge=2, le=10),
    db: AsyncSession = Depends(get_db_session),
):
    query = (
        select(Report.fiscal_year, func.count(RiskItem.id))
        .join(RiskItem, RiskItem.report_id == Report.id)
        .where(Report.company_id == company_id)
        .group_by(Report.fiscal_year)
        .order_by(Report.fiscal_year)
    )

    result = await db.execute(query)
    trends = result.all()

    return {"trends": [{"year": year, "risk_count": count} for year, count in trends]}

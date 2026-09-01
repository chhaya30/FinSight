from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logging import get_logger
from app.db.base import Company, EvolutionEntry, Report, RiskItem
from app.db.session import get_db_session
from app.models.comparison import (
    ComparisonRequest,
    ComparisonResponse,
    EvolutionSummary,
)

logger = get_logger(__name__)

router = APIRouter()


@router.post("/compare", response_model=ComparisonResponse)
async def compare_years(
    request: ComparisonRequest,
    db: AsyncSession = Depends(get_db_session),
):
    company = await db.get(Company, request.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    report_current = await db.execute(
        select(Report).where(
            Report.company_id == request.company_id,
            Report.fiscal_year == request.year_current,
        )
    )
    report_current = report_current.scalar_one_or_none()
    if not report_current:
        raise HTTPException(
            status_code=404,
            detail=f"Report for FY{request.year_current} not found",
        )

    report_prev = await db.execute(
        select(Report).where(
            Report.company_id == request.company_id,
            Report.fiscal_year == request.year_previous,
        )
    )
    report_prev = report_prev.scalar_one_or_none()
    if not report_prev:
        raise HTTPException(
            status_code=404,
            detail=f"Report for FY{request.year_previous} not found",
        )

    risks_current = await db.execute(
        select(RiskItem).where(RiskItem.report_id == report_current.id)
    )
    risks_current = risks_current.scalars().all()

    risks_prev = await db.execute(select(RiskItem).where(RiskItem.report_id == report_prev.id))
    risks_prev = risks_prev.scalars().all()

    existing_evolutions = await db.execute(
        select(EvolutionEntry).where(
            EvolutionEntry.risk_item_id_prev.in_([r.id for r in risks_prev])
            | EvolutionEntry.risk_item_id_current.in_([r.id for r in risks_current])
        )
    )
    existing_evolutions = existing_evolutions.scalars().all()

    if existing_evolutions:
        from app.models.comparison import EvolutionEntryDetailResponse
        from app.models.risk import RiskItemResponse

        current_ids = {e.risk_item_id_current for e in existing_evolutions}
        new_risks = [r for r in risks_current if r.id not in current_ids]

        prev_ids = {e.risk_item_id_prev for e in existing_evolutions}
        removed_risks = [r for r in risks_prev if r.id not in prev_ids]

        severity_up = []
        severity_down = []
        modified = []

        for evo in existing_evolutions:
            detail = EvolutionEntryDetailResponse.model_validate(evo)
            if evo.change_type == "SEVERITY_UP":
                severity_up.append(detail)
            elif evo.change_type == "SEVERITY_DOWN":
                severity_down.append(detail)
            elif evo.change_type == "MODIFIED":
                modified.append(detail)

        return ComparisonResponse(
            company_id=request.company_id,
            year_current=request.year_current,
            year_previous=request.year_previous,
            new_risks=[RiskItemResponse.model_validate(r) for r in new_risks],
            removed_risks=[RiskItemResponse.model_validate(r) for r in removed_risks],
            severity_increased=severity_up,
            severity_decreased=severity_down,
            modified_risks=modified,
            total_changes=len(existing_evolutions),
            processing_time_seconds=0.0,
        )

    return ComparisonResponse(
        company_id=request.company_id,
        year_current=request.year_current,
        year_previous=request.year_previous,
        new_risks=[],
        removed_risks=[],
        severity_increased=[],
        severity_decreased=[],
        modified_risks=[],
        total_changes=0,
        processing_time_seconds=0.0,
    )


@router.get("/{company_id}/evolution", response_model=ComparisonResponse)
async def get_evolution(
    company_id: UUID,
    year_current: int = Query(...),
    year_previous: int = Query(...),
    db: AsyncSession = Depends(get_db_session),
):
    request = ComparisonRequest(
        company_id=company_id,
        year_current=year_current,
        year_previous=year_previous,
    )
    return await compare_years(request, db)


@router.get("/{company_id}/summary", response_model=EvolutionSummary)
async def get_evolution_summary(
    company_id: UUID,
    year_current: int = Query(...),
    year_previous: int = Query(...),
    db: AsyncSession = Depends(get_db_session),
):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    report_current = await db.execute(
        select(Report).where(
            Report.company_id == company_id,
            Report.fiscal_year == year_current,
        )
    )
    report_current = report_current.scalar_one_or_none()

    report_prev = await db.execute(
        select(Report).where(
            Report.company_id == company_id,
            Report.fiscal_year == year_previous,
        )
    )
    report_prev = report_prev.scalar_one_or_none()

    if not report_current or not report_prev:
        raise HTTPException(status_code=404, detail="Reports not found for both years")

    risks_current = await db.execute(
        select(RiskItem).where(RiskItem.report_id == report_current.id)
    )
    risks_current = risks_current.scalars().all()

    risks_prev = await db.execute(select(RiskItem).where(RiskItem.report_id == report_prev.id))
    risks_prev = risks_prev.scalars().all()

    evolutions = await db.execute(
        select(EvolutionEntry).where(
            EvolutionEntry.risk_item_id_prev.in_([r.id for r in risks_prev])
            | EvolutionEntry.risk_item_id_current.in_([r.id for r in risks_current])
        )
    )
    evolutions = evolutions.scalars().all()

    new_count = sum(1 for e in evolutions if e.change_type == "NEW")
    removed_count = sum(1 for e in evolutions if e.change_type == "REMOVED")
    severity_up = sum(1 for e in evolutions if e.change_type == "SEVERITY_UP")
    severity_down = sum(1 for e in evolutions if e.change_type == "SEVERITY_DOWN")
    modified = sum(1 for e in evolutions if e.change_type == "MODIFIED")

    current_categories = {}
    for r in risks_current:
        current_categories[r.category] = current_categories.get(r.category, 0) + 1

    prev_categories = {}
    for r in risks_prev:
        prev_categories[r.category] = prev_categories.get(r.category, 0) + 1

    top_new = sorted(current_categories.items(), key=lambda x: x[1], reverse=True)[:5]
    top_removed = sorted(prev_categories.items(), key=lambda x: x[1], reverse=True)[:5]

    return EvolutionSummary(
        company_id=company_id,
        period=f"{year_previous}-{year_current}",
        total_risks_current=len(risks_current),
        total_risks_previous=len(risks_prev),
        net_change=len(risks_current) - len(risks_prev),
        new_risks_count=new_count,
        removed_risks_count=removed_count,
        severity_changes={
            "increased": severity_up,
            "decreased": severity_down,
            "modified": modified,
        },
        top_new_categories=[{"category": c, "count": cnt} for c, cnt in top_new],
        top_removed_categories=[{"category": c, "count": cnt} for c, cnt in top_removed],
        ai_narrative=(
            f"Risk profile evolved from {len(risks_prev)} risks in FY{year_previous} "
            f"to {len(risks_current)} risks in FY{year_current}."
        ),
    )


@router.get("/{company_id}/timeline")
async def get_risk_timeline(
    company_id: UUID,
    category: str | None = Query(None),
    years: int = Query(5, ge=2, le=10),
    db: AsyncSession = Depends(get_db_session),
):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    query = (
        select(Report.fiscal_year, func.count(RiskItem.id))
        .join(RiskItem, RiskItem.report_id == Report.id)
        .where(Report.company_id == company_id)
        .group_by(Report.fiscal_year)
        .order_by(Report.fiscal_year.desc())
        .limit(years)
    )

    if category:
        query = query.where(RiskItem.category == category)

    result = await db.execute(query)
    timeline = result.all()

    return {"timeline": [{"year": year, "risk_count": count} for year, count in timeline]}

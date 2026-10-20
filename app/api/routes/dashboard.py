from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes._phase2_helpers import load_phase2_records
from app.db.base import Company, Report, RiskItem
from app.db.session import get_db_session
from app.intelligence.dashboard import ExecutiveDashboardService
from app.models.dashboard import DashboardCompany, DashboardReport, ExecutiveDashboardResponse, HeatmapResponse

router = APIRouter()


@router.get("/executive", response_model=ExecutiveDashboardResponse)
async def get_executive_dashboard(
    company_id: UUID,
    year_current: int = Query(..., ge=1900, le=2100),
    year_previous: int = Query(..., ge=1900, le=2100),
    db: AsyncSession = Depends(get_db_session),
) -> ExecutiveDashboardResponse:
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    reports = await db.execute(
        select(Report).where(
            Report.company_id == company_id,
            Report.fiscal_year.in_([year_previous, year_current]),
        )
    )
    reports_by_year = {report.fiscal_year: report for report in reports.scalars().all()}
    if year_previous not in reports_by_year or year_current not in reports_by_year:
        raise HTTPException(status_code=404, detail="Reports not found for both years")
    previous = reports_by_year[year_previous]
    current = reports_by_year[year_current]
    previous_risks = await db.execute(select(RiskItem).where(RiskItem.report_id == previous.id))
    current_risks = await db.execute(select(RiskItem).where(RiskItem.report_id == current.id))
    previous_risk_items = previous_risks.scalars().all()
    current_risk_items = current_risks.scalars().all()
    records, explanations, financial = await load_phase2_records(
        previous,
        current,
        previous_risk_items,
        current_risk_items,
        session=db,
    )
    return ExecutiveDashboardService().build(
        company=DashboardCompany(id=company.id, name=company.name, sector=company.sector),
        previous_report=DashboardReport(
            year=previous.fiscal_year, report_id=previous.id, source_file=previous.source_file
        ),
        current_report=DashboardReport(
            year=current.fiscal_year, report_id=current.id, source_file=current.source_file
        ),
        total_previous=len(previous_risk_items),
        total_current=len(current_risk_items),
        records=records,
        explanations=explanations,
        financial=financial,
    )


@router.get("/heatmap", response_model=HeatmapResponse)
async def get_risk_heatmap(
    company_id: UUID = Query(...),
    year: int | None = Query(None, ge=1900, le=2100),
    db: AsyncSession = Depends(get_db_session),
) -> HeatmapResponse:
    """Get risk heatmap data: category x severity matrix with counts and scores."""
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # If year is specified, get risks for that year; otherwise get all risks for the company
    if year:
        report = await db.execute(
            select(Report).where(
                Report.company_id == company_id,
                Report.fiscal_year == year,
            )
        )
        report = report.scalar_one_or_none()
        if not report:
            raise HTTPException(status_code=404, detail=f"Report for FY{year} not found")
        report_ids = [report.id]
    else:
        reports = await db.execute(
            select(Report.id).where(Report.company_id == company_id)
        )
        report_ids = [r for r in reports.scalars().all()]

    if not report_ids:
        return HeatmapResponse(cells=[], total_risks=0)

    risks = await db.execute(
        select(RiskItem).where(RiskItem.report_id.in_(report_ids))
    )
    risk_items = risks.scalars().all()

    if not risk_items:
        return HeatmapResponse(cells=[], total_risks=0)

    # Aggregate by category and severity
    severity_order = {"critical": 9, "high": 7, "medium": 5, "low": 3, "informational": 1}
    category_severity: dict[str, dict[str, list[RiskItem]]] = {}

    for risk in risk_items:
        cat = risk.category or "Uncategorized"
        sev = (risk.severity or "medium").lower()
        if cat not in category_severity:
            category_severity[cat] = {}
        if sev not in category_severity[cat]:
            category_severity[cat][sev] = []
        category_severity[cat][sev].append(risk)

    cells = []
    for category, severities in category_severity.items():
        for severity, risks_in_cell in severities.items():
            count = len(risks_in_cell)
            avg_confidence = sum(r.confidence_score for r in risks_in_cell) / count
            # Score = average severity weight * average confidence
            severity_weight = severity_order.get(severity, 5)
            score = severity_weight * avg_confidence
            cells.append(
                HeatmapCell(
                    category=category,
                    severity=severity,  # type: ignore
                    count=count,
                    score=round(score, 1),
                )
            )

    return HeatmapResponse(cells=cells, total_risks=len(risk_items))
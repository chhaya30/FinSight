from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes._phase2_helpers import load_phase2_records
from app.db.base import Company, Report, RiskItem
from app.db.session import get_db_session
from app.intelligence.dashboard import ExecutiveDashboardService
from app.models.dashboard import DashboardCompany, DashboardReport, ExecutiveDashboardResponse

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
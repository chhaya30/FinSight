from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config.logging import get_logger
from app.db.base import Company, Report
from app.db.session import get_db_session
from app.models.company import (
    CompanyCreate,
    CompanyDetailResponse,
    CompanyListResponse,
    CompanyResponse,
    CompanyUpdate,
)

logger = get_logger(__name__)

router = APIRouter()


@router.post("", response_model=CompanyResponse, status_code=201)
async def create_company(
    company: CompanyCreate,
    db: AsyncSession = Depends(get_db_session),
):
    existing = await db.execute(select(Company).where(Company.name == company.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Company already exists")

    db_company = Company(**company.model_dump())
    db.add(db_company)
    await db.commit()
    await db.refresh(db_company)

    return CompanyResponse.model_validate(db_company)


@router.get("", response_model=CompanyListResponse)
async def list_companies(
    sector: str | None = Query(None),
    exchange: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
):
    query = select(Company)

    if sector:
        query = query.where(Company.sector == sector)
    if exchange:
        query = query.where(Company.listed_exchange == exchange)
    if search:
        query = query.where(Company.name.ilike(f"%{search}%"))

    query = query.order_by(Company.name)

    total_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(total_query)

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    companies = result.scalars().all()

    return CompanyListResponse(
        companies=[CompanyResponse.model_validate(c) for c in companies],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{company_id}", response_model=CompanyDetailResponse)
async def get_company(
    company_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    company = await db.get(Company, company_id, options=[selectinload(Company.reports)])
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    reports_count = len(company.reports) if company.reports else 0
    latest_year = (
        max((r.fiscal_year for r in company.reports), default=None) if company.reports else None
    )

    from sqlalchemy import func, select

    from app.db.base import RiskItem as RiskItemModel

    risk_count = 0
    if company.reports:
        report_ids = [r.id for r in company.reports]
        result = await db.execute(
            select(func.count(RiskItemModel.id)).where(RiskItemModel.report_id.in_(report_ids))
        )
        risk_count = result.scalar() or 0

    return CompanyDetailResponse(
        **CompanyResponse.model_validate(company).model_dump(),
        reports_count=reports_count,
        latest_report_year=latest_year,
        risk_count=risk_count,
    )


@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: UUID,
    company_update: CompanyUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    update_data = company_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(company, field, value)

    await db.commit()
    await db.refresh(company)

    return CompanyResponse.model_validate(company)


@router.delete("/{company_id}")
async def delete_company(
    company_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    await db.delete(company)
    await db.commit()

    return {"message": "Company deleted successfully"}


@router.get("/{company_id}/reports")
async def get_company_reports(
    company_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    result = await db.execute(
        select(Report).where(Report.company_id == company_id).order_by(Report.fiscal_year.desc())
    )
    reports = result.scalars().all()

    return {"reports": reports}


@router.get("/sectors/list")
async def list_sectors(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Company.sector).distinct().where(Company.sector.isnot(None)))
    sectors = [s for s in result.scalars().all() if s]
    return {"sectors": sorted(sectors)}


@router.get("/exchanges/list")
async def list_exchanges(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(
        select(Company.listed_exchange).distinct().where(Company.listed_exchange.isnot(None))
    )
    exchanges = [e for e in result.scalars().all() if e]
    return {"exchanges": sorted(exchanges)}

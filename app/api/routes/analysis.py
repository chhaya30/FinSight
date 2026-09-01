from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config.logging import get_logger
from app.db.base import Report
from app.db.session import get_db_session
from app.models.risk import (
    RiskExtractionRequest,
    RiskExtractionResponse,
    RiskItemListResponse,
    RiskItemResponse,
)

logger = get_logger(__name__)

router = APIRouter()


@router.post("/extract", response_model=RiskExtractionResponse)
async def extract_risks(
    request: RiskExtractionRequest,
    db: AsyncSession = Depends(get_db_session),
):
    report = await db.get(Report, request.report_id, options=[selectinload(Report.company)])
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.processing_status != "completed":
        raise HTTPException(status_code=400, detail="Report not yet processed")

    from app.db.base import RiskItem as RiskItemModel
    from app.models.document import PageContent

    result = await db.execute(
        select(RiskItemModel).where(RiskItemModel.report_id == request.report_id)
    )
    existing_risks = result.scalars().all()

    if existing_risks and not request.force_reprocess:
        return RiskExtractionResponse(
            report_id=request.report_id,
            risks_extracted=len(existing_risks),
            risks=[RiskItemResponse.model_validate(r) for r in existing_risks],
            processing_time_seconds=0.0,
        )

    from app.config.settings import get_settings
    from app.ingestion import create_adaptive_fallback_router
    from app.processing import clean_text, normalize_text
    from app.risk_engine.pipeline import create_pipeline

    settings = get_settings()
    file_path = Path(settings.UPLOAD_DIR) / report.source_file

    fallback_router = create_adaptive_fallback_router()
    extracted_doc = fallback_router.process(file_path)

    pages = [page.text for page in extracted_doc.pages]
    cleaned_pages = [clean_text(page) for page in pages]
    normalized_pages = [normalize_text(page) for page in cleaned_pages]

    page_contents = [
        PageContent(page_number=i + 1, text=page, char_count=len(page))
        for i, page in enumerate(normalized_pages)
    ]

    pipeline = create_pipeline()
    result = pipeline.run(page_contents, str(request.report_id))

    for risk in result.risks:
        risk_model = RiskItemModel(
            report_id=request.report_id,
            category=risk.category,
            severity=risk.severity,
            confidence_score=risk.confidence_score,
            summary=risk.summary,
            source_page=risk.candidate.source_page,
            source_paragraph=risk.candidate.text[:500],
            entities=[e.model_dump() for e in risk.entities],
            metadata={
                "source_section": risk.candidate.source_section,
                "paragraph_index": risk.candidate.paragraph_index,
            },
        )
        db.add(risk_model)

    await db.commit()

    return RiskExtractionResponse(
        report_id=request.report_id,
        risks_extracted=len(result.risks),
        risks=[RiskItemResponse.model_validate(r) for r in result.risks],
        processing_time_seconds=result.processing_time,
    )


@router.get("/{report_id}/risks", response_model=RiskItemListResponse)
async def get_report_risks(
    report_id: UUID,
    category: str | None = Query(None),
    severity: str | None = Query(None),
    min_confidence: float | None = Query(None, ge=0, le=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
):
    report = await db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    from app.db.base import RiskItem as RiskItemModel

    query = select(RiskItemModel).where(RiskItemModel.report_id == report_id)

    if category:
        query = query.where(RiskItemModel.category == category)
    if severity:
        query = query.where(RiskItemModel.severity == severity)
    if min_confidence:
        query = query.where(RiskItemModel.confidence_score >= min_confidence)

    query = query.order_by(RiskItemModel.confidence_score.desc())

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


@router.get("/risks/{risk_id}", response_model=RiskItemResponse)
async def get_risk(
    risk_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    from app.db.base import RiskItem as RiskItemModel

    risk = await db.get(RiskItemModel, risk_id)
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")

    return RiskItemResponse.model_validate(risk)


@router.get("/company/{company_id}/risks", response_model=RiskItemListResponse)
async def get_company_risks(
    company_id: UUID,
    fiscal_year: int | None = Query(None),
    category: str | None = Query(None),
    severity: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
):
    from app.db.base import RiskItem as RiskItemModel

    query = (
        select(RiskItemModel)
        .join(Report, RiskItemModel.report_id == Report.id)
        .where(Report.company_id == company_id)
    )

    if fiscal_year:
        query = query.where(Report.fiscal_year == fiscal_year)
    if category:
        query = query.where(RiskItemModel.category == category)
    if severity:
        query = query.where(RiskItemModel.severity == severity)

    query = query.order_by(RiskItemModel.confidence_score.desc())

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


@router.get("/categories/stats")
async def get_category_stats(
    company_id: UUID | None = Query(None),
    fiscal_year: int | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    from app.db.base import RiskItem as RiskItemModel

    query = (
        select(RiskItemModel.category, func.count(RiskItemModel.id))
        .join(Report, RiskItemModel.report_id == Report.id)
        .group_by(RiskItemModel.category)
    )

    if company_id:
        query = query.where(Report.company_id == company_id)
    if fiscal_year:
        query = query.where(Report.fiscal_year == fiscal_year)

    result = await db.execute(query)
    stats = result.all()

    return {"categories": [{"category": cat, "count": cnt} for cat, cnt in stats]}


@router.get("/severity/stats")
async def get_severity_stats(
    company_id: UUID | None = Query(None),
    fiscal_year: int | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    from app.db.base import RiskItem as RiskItemModel

    query = (
        select(RiskItemModel.severity, func.count(RiskItemModel.id))
        .join(Report, RiskItemModel.report_id == Report.id)
        .group_by(RiskItemModel.severity)
    )

    if company_id:
        query = query.where(Report.company_id == company_id)
    if fiscal_year:
        query = query.where(Report.fiscal_year == fiscal_year)

    result = await db.execute(query)
    stats = result.all()

    return {"severity": [{"severity": sev, "count": cnt} for sev, cnt in stats]}

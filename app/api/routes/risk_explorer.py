from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.industry_intelligence import get_industry_provider
from app.api.routes.market_intelligence import get_market_provider
from app.db.base import Company, DocumentChunk, Report, RiskItem
from app.db.session import get_db_session
from app.intelligence.industry import (
    IndustryIntelligenceProvider,
    IndustryIntelligenceService,
)
from app.intelligence.market import MarketIntelligenceProvider, MarketIntelligenceService
from app.intelligence.risk_explorer import compare_report_risks, evolution_by_risk_id
from app.intelligence.classification_confidence import assess_classification_confidence
from app.models.comparison import RiskEvolutionRecord
from app.models.risk_explorer import (
    RiskExplorerDetailResponse,
    ClassificationConfidenceDetail,
    RiskExplorerEvidence,
    RiskExplorerItem,
    RiskExplorerListResponse,
    RiskExplorerRiskVersion,
)

router = APIRouter()


@router.get("", response_model=RiskExplorerListResponse)
async def list_risk_explorer_items(
    company_id: UUID | None = Query(None),
    category: str | None = Query(None),
    severity: str | None = Query(None),
    year: int | None = Query(None, ge=1900, le=2100),
    status: str | None = Query(None),
    search: str | None = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> RiskExplorerListResponse:
    all_companies = list((await db.execute(select(Company).order_by(Company.name))).scalars().all())
    companies = [c for c in all_companies if not company_id or c.id == str(company_id)]
    company_ids = [company.id for company in companies]
    if not company_ids:
        return RiskExplorerListResponse(
            items=[], total=0, page=page, page_size=page_size,
            companies=[{"id": str(c.id), "name": c.name} for c in all_companies],
            categories=[], severities=[], years=[],
            statuses=["NEW", "REMOVED", "UNCHANGED", "MODIFIED", "ESCALATED", "DE-ESCALATED", "UNCOMPARED"],
        )

    reports = list((await db.execute(
        select(Report).where(Report.company_id.in_(company_ids)).order_by(Report.fiscal_year)
    )).scalars().all())
    reports_by_company: dict[str, list[Report]] = {}
    for report in reports:
        reports_by_company.setdefault(report.company_id, []).append(report)

    report_ids = [report.id for report in reports]
    risks = list((await db.execute(
        select(RiskItem).where(RiskItem.report_id.in_(report_ids)).order_by(RiskItem.confidence_score.desc())
    )).scalars().all()) if report_ids else []
    risks_by_report: dict[str, list[RiskItem]] = {}
    for risk in risks:
        risks_by_report.setdefault(risk.report_id, []).append(risk)

    company_by_id = {company.id: company for company in companies}
    available_categories = sorted({risk.category for risk in risks})
    available_severities = sorted({risk.severity for risk in risks})
    available_years = sorted({report.fiscal_year for report in reports}, reverse=True)
    rows: list[RiskExplorerItem] = []
    available_statuses = {"NEW", "REMOVED", "UNCHANGED", "MODIFIED", "ESCALATED", "DE-ESCALATED", "UNCOMPARED"}

    for company_key, company_reports in reports_by_company.items():
        if year is None:
            current_report = company_reports[-1]
        else:
            current_report = next((r for r in company_reports if r.fiscal_year == year), None)
            if current_report is None:
                continue
        previous_report = next(
            (r for r in reversed(company_reports) if r.fiscal_year < current_report.fiscal_year), None
        )
        current_risks = risks_by_report.get(current_report.id, [])
        previous_risks = risks_by_report.get(previous_report.id, []) if previous_report else []
        evolution_records: list[RiskEvolutionRecord] = []
        if previous_report:
            evolution_records, _, _ = await compare_report_risks(
                previous_report, current_report, previous_risks, current_risks
            )
        evolution_index = evolution_by_risk_id(evolution_records)

        company = company_by_id[company_key]
        for risk in current_risks:
            record = evolution_index.get(risk.id)
            risk_status = record.change_type.value if record else "UNCOMPARED"
            if category and risk.category.casefold() != category.casefold():
                continue
            if severity and risk.severity.casefold() != severity.casefold():
                continue
            if status and risk_status.casefold() != status.casefold():
                continue
            if search and search.casefold() not in f"{company.name} {risk.category} {risk.severity} {risk.summary}".casefold():
                continue
            rows.append(RiskExplorerItem(
                risk_id=UUID(risk.id), company_id=UUID(company.id), company_name=company.name,
                report_id=UUID(current_report.id), year=current_report.fiscal_year,
                comparison_year=current_report.fiscal_year,
                category=risk.category, severity=risk.severity, status=risk_status,
                title=risk.summary[:120], summary=risk.summary, confidence=risk.confidence_score,
                source_document=current_report.source_file, source_page=risk.source_page,
                previous_risk_id=UUID(record.year_1_risk_id) if record and record.year_1_risk_id else None,
            ))

        for record in evolution_records:
            if record.year_2_risk_id or not record.year_1_risk_id:
                continue
            removed = next((r for r in previous_risks if r.id == record.year_1_risk_id), None)
            if removed is None:
                continue
            if category and removed.category.casefold() != category.casefold():
                continue
            if severity and removed.severity.casefold() != severity.casefold():
                continue
            if status and status.casefold() != "removed":
                continue
            if search and search.casefold() not in f"{company.name} {removed.category} {removed.severity} {removed.summary}".casefold():
                continue
            rows.append(RiskExplorerItem(
                risk_id=UUID(removed.id), company_id=UUID(company.id), company_name=company.name,
                report_id=UUID(previous_report.id), year=previous_report.fiscal_year,
                comparison_year=current_report.fiscal_year,
                category=removed.category, severity=removed.severity, status="REMOVED",
                title=removed.summary[:120], summary=removed.summary, confidence=removed.confidence_score,
                source_document=previous_report.source_file, source_page=removed.source_page,
            ))

    rows.sort(key=lambda item: (item.year, item.confidence), reverse=True)
    total = len(rows)
    return RiskExplorerListResponse(
        items=rows[(page - 1) * page_size:page * page_size], total=total,
        page=page, page_size=page_size,
        companies=[{"id": str(c.id), "name": c.name} for c in all_companies],
        categories=available_categories, severities=available_severities,
        years=available_years, statuses=sorted(available_statuses),
    )


@router.get("/{risk_id}", response_model=RiskExplorerDetailResponse)
async def get_risk_explorer_detail(
    risk_id: UUID,
    year: int | None = Query(None, ge=1900, le=2100),
    db: AsyncSession = Depends(get_db_session),
    market_provider: MarketIntelligenceProvider = Depends(get_market_provider),
    industry_provider: IndustryIntelligenceProvider = Depends(get_industry_provider),
) -> RiskExplorerDetailResponse:
    risk = await db.get(RiskItem, str(risk_id))
    if risk is None:
        raise HTTPException(status_code=404, detail="Risk not found")
    report = await db.get(Report, risk.report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Risk report not found")
    company = await db.get(Company, report.company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Risk company not found")

    reports = list((await db.execute(
        select(Report).where(Report.company_id == company.id).order_by(Report.fiscal_year)
    )).scalars().all())
    if year is not None:
        current_report = next((item for item in reports if item.fiscal_year == year), None)
        if current_report is None or report not in reports:
            raise HTTPException(status_code=404, detail="Risk report year not found")
        previous_report = next(
            (item for item in reversed(reports) if item.fiscal_year < current_report.fiscal_year), None
        )
        if report.id != current_report.id and (
            previous_report is None or report.id != previous_report.id
        ):
            raise HTTPException(status_code=404, detail="Risk is not part of the requested comparison")
    else:
        report_index = next((i for i, item in enumerate(reports) if item.id == report.id), 0)
        previous_report = reports[report_index - 1] if report_index > 0 else None
        current_report = reports[report_index + 1] if report_index + 1 < len(reports) else report
        if report_index > 0:
            current_report = report
    previous_risks: list[RiskItem] = []
    current_risks: list[RiskItem] = []
    records: list[RiskEvolutionRecord] = []
    explanations = []
    financial_analysis = None
    if previous_report and current_report.id != previous_report.id:
        previous_risks = list((await db.execute(select(RiskItem).where(RiskItem.report_id == previous_report.id))).scalars().all())
        current_risks = list((await db.execute(select(RiskItem).where(RiskItem.report_id == current_report.id))).scalars().all())
        records, explanations, financial_analysis = await compare_report_risks(
            previous_report, current_report, previous_risks, current_risks,
            include_financial=True,
        )
    elif current_report.id != report.id:
        # The selected risk is in the earliest report; compare it with its next report.
        previous_report = report
        previous_risks = list((await db.execute(select(RiskItem).where(RiskItem.report_id == report.id))).scalars().all())
        current_risks = list((await db.execute(select(RiskItem).where(RiskItem.report_id == current_report.id))).scalars().all())
        records, explanations, financial_analysis = await compare_report_risks(
            previous_report, current_report, previous_risks, current_risks,
            include_financial=True,
        )

    record = next((item for item in records if risk.id in (item.year_1_risk_id, item.year_2_risk_id)), None)
    explanation = next((item for item in explanations if item.source_record is record), None)
    evolution_index = evolution_by_risk_id(records)
    status = evolution_index[risk.id].change_type.value if risk.id in evolution_index else "UNCOMPARED"
    current_item = next((item for item in current_risks if record and item.id == record.year_2_risk_id), None)
    previous_item = next((item for item in previous_risks if record and item.id == record.year_1_risk_id), None)
    if current_item is None and previous_item is None:
        if risk.report_id == current_report.id:
            current_item = risk
        else:
            previous_item = risk

    async def version(item: RiskItem | None, source_report: Report | None):
        if item is None or source_report is None:
            return None
        chunk = None
        if item.source_page:
            chunks = (await db.execute(
                select(DocumentChunk).where(DocumentChunk.report_id == source_report.id)
            )).scalars().all()
            chunk = next((c for c in chunks if c.page_start is not None and c.page_end is not None
                          and c.page_start <= item.source_page <= c.page_end), None)
        text = item.source_paragraph or item.summary
        evidence = RiskExplorerEvidence(
            document=source_report.source_file,
            source_url=source_report.source_url or (item.extra_metadata or {}).get("source_url"),
            year=source_report.fiscal_year,
            page=item.source_page, chunk_id=UUID(chunk.id) if chunk else None,
            source="risk_items.source_paragraph" if item.source_paragraph else "risk_items.summary",
            text=text,
        )
        assessment = assess_classification_confidence(
            category=item.category, severity=item.severity,
            stored_confidence=item.confidence_score, evidence_text=text,
            source_document=source_report.source_url or source_report.source_file, page=item.source_page,
            chunk_available=chunk is not None,
        )
        confidence_detail = ClassificationConfidenceDetail(
            category_confidence=assessment.category,
            severity_confidence=assessment.severity,
            classification_confidence=assessment.classification,
            evidence_quality=assessment.evidence_quality,
            low_confidence=assessment.low_confidence,
            confidence_reason=assessment.reason,
            supporting_evidence=[evidence] if text else [],
        )
        return RiskExplorerRiskVersion(
            risk_id=UUID(item.id), year=source_report.fiscal_year, category=item.category,
            severity=item.severity, confidence=item.confidence_score,
            title=item.summary[:120], summary=item.summary, evidence=evidence,
            classification_assessment=confidence_detail,
        )

    previous_for_risk = previous_report or (report if previous_item else None)
    current_for_risk = current_report or report
    current_version = await version(current_item, current_report if current_item else current_for_risk)
    previous_version = await version(previous_item, previous_for_risk)

    if not records:
        status = "UNCOMPARED"
    market_signals = await MarketIntelligenceService(market_provider).fetch_for_company(
        str(company.id), company.name, records
    )
    industry_signals = await IndustryIntelligenceService(industry_provider).analyze_company(
        str(company.id), company.name, company.sector, records
    )
    related_market = [
        item for item in market_signals.related_risks
        if record is not None and risk.id in (item.risk_item_id_prev, item.risk_item_id_current)
    ]
    market_signals = market_signals.model_copy(update={
        "related_risks": related_market,
    })
    assessments = [
        item for item in industry_signals.assessments
        if record is not None and item.risk_id == risk.id
    ]
    supporting_theme_ids = {theme_id for item in assessments for theme_id in item.supporting_themes}
    industry_signals = industry_signals.model_copy(update={
        "assessments": assessments,
        "themes": [theme for theme in industry_signals.themes if theme.id in supporting_theme_ids],
        "peer_comparisons": [
            item for item in industry_signals.peer_comparisons
            if record is not None and item.category.casefold() == risk.category.casefold()
        ],
    })
    return RiskExplorerDetailResponse(
        company_id=UUID(company.id), company_name=company.name, status=status,
        current_risk=current_version, previous_risk=previous_version,
        explanation=explanation, financial_analysis=financial_analysis,
        market_signals=market_signals, industry_signals=industry_signals,
    )

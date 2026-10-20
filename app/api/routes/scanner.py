from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.industry_intelligence import get_industry_provider
from app.api.routes.market_intelligence import get_market_provider
from app.db.base import Company, Report, RiskItem
from app.db.session import get_db_session
from app.intelligence.industry import (
    IndustryIntelligenceProvider,
    IndustryIntelligenceService,
)
from app.intelligence.market import MarketIntelligenceProvider, MarketIntelligenceService
from app.intelligence.risk_explorer import compare_report_risks
from app.intelligence.scanner import (
    SCORE_WEIGHTS,
    SEVERITY_SCORES,
    STATUS_SCORES,
    attach_match,
    build_result,
    matches_criteria,
)
from app.models.comparison import RiskEvolutionRecord
from app.models.scanner import (
    ContributingFactor,
    ScannerEvidence,
    ScannerOptionsResponse,
    ScannerRequest,
    ScannerResponse,
)

router = APIRouter()
_STATUSES = ["NEW", "REMOVED", "UNCHANGED", "MODIFIED", "ESCALATED", "DE-ESCALATED", "UNCOMPARED"]


@router.get("/options", response_model=ScannerOptionsResponse)
async def scanner_options(db: AsyncSession = Depends(get_db_session)) -> ScannerOptionsResponse:
    companies = list((await db.execute(select(Company).order_by(Company.name))).scalars().all())
    reports = list((await db.execute(select(Report).order_by(Report.fiscal_year))).scalars().all())
    risks = list((await db.execute(select(RiskItem))).scalars().all())
    return ScannerOptionsResponse(
        companies=[{"id": str(company.id), "name": company.name, "sector": company.sector} for company in companies],
        sectors=sorted({company.sector for company in companies if company.sector}),
        years=sorted({report.fiscal_year for report in reports}, reverse=True),
        categories=sorted({risk.category for risk in risks}),
        severities=sorted({risk.severity_label for risk in risks if risk.severity_label}),
        statuses=_STATUSES,
        factor_operators={
            "category": ["eq", "observed"],
            "status": ["eq", "observed"],
            "severity": ["eq", "gte", "observed"],
            "financial_signal": ["eq", "observed"],
            "market_signal": ["eq", "observed"],
            "industry_signal": ["eq", "observed"],
            "evidence_quality": ["gte", "observed"],
            "classification_confidence": ["gte", "observed"],
        },
    )


@router.post("/run", response_model=ScannerResponse)
async def run_scanner(
    request: ScannerRequest,
    db: AsyncSession = Depends(get_db_session),
    market_provider: MarketIntelligenceProvider = Depends(get_market_provider),
    industry_provider: IndustryIntelligenceProvider = Depends(get_industry_provider),
) -> ScannerResponse:
    companies_query = select(Company).order_by(Company.name)
    if request.company_ids:
        companies_query = companies_query.where(Company.id.in_([str(value) for value in request.company_ids]))
    if request.sectors:
        companies_query = companies_query.where(Company.sector.in_(request.sectors))
    companies = list((await db.execute(companies_query)).scalars().all())
    all_results = []

    for company in companies:
        reports = list((await db.execute(
            select(Report).where(Report.company_id == company.id).order_by(Report.fiscal_year)
        )).scalars().all())
        if request.year_current is None:
            current_report = reports[-1] if reports else None
        else:
            current_report = next((r for r in reports if r.fiscal_year == request.year_current), None)
        if current_report is None:
            continue
        if request.year_previous is not None:
            previous_report = next((r for r in reports if r.fiscal_year == request.year_previous), None)
        else:
            previous_report = next(
                (r for r in reversed(reports) if r.fiscal_year < current_report.fiscal_year), None
            )
        current_risks = list((await db.execute(
            select(RiskItem).where(RiskItem.report_id == current_report.id)
        )).scalars().all())
        previous_risks = list((await db.execute(
            select(RiskItem).where(RiskItem.report_id == previous_report.id)
        )).scalars().all()) if previous_report else []

        records: list[RiskEvolutionRecord] = []
        explanations = []
        financial_analysis = None
        if previous_report and previous_report.fiscal_year < current_report.fiscal_year:
            records, explanations, financial_analysis = await compare_report_risks(
                previous_report, current_report, previous_risks, current_risks,
                include_financial=True,
                session=db,
            )
        market = await MarketIntelligenceService(market_provider).fetch_for_company(
            str(company.id), company.name, records
        )
        industry = await IndustryIntelligenceService(industry_provider).analyze_company(
            str(company.id), company.name, company.sector, records
        )
        current_by_id = {risk.id: risk for risk in current_risks}
        previous_by_id = {risk.id: risk for risk in previous_risks}
        explanations_by_pair = {
            (item.year_1_risk_id, item.year_2_risk_id): item for item in explanations
        }
        record_set = records if records else [None] * len(current_risks)
        for index, record in enumerate(record_set):
            if record is None:
                risk = current_risks[index]
                current_risk = risk
                previous_risk = None
                status = "UNCOMPARED"
            else:
                current_risk = current_by_id.get(record.year_2_risk_id)
                previous_risk = previous_by_id.get(record.year_1_risk_id)
                risk = current_risk or previous_risk
                if risk is None:
                    continue
                status = record.change_type.value
            pair = (record.year_1_risk_id, record.year_2_risk_id) if record else (None, None)
            explanation = explanations_by_pair.get(pair)
            evidence = _risk_evidence(record, current_report, previous_report) if record else _risk_evidence_from_item(risk, current_report)
            factors = _build_factors(
                risk=risk,
                current_risk=current_risk,
                previous_risk=previous_risk,
                record=record,
                explanation=explanation,
                financial_analysis=financial_analysis,
                market=market,
                industry=industry,
                evidence=evidence,
                status=status,
            )
            result = build_result(
                risk_id=risk.id,
                company_id=company.id,
                company_name=company.name,
                sector=company.sector,
                report_year=current_report.fiscal_year,
                previous_year=previous_report.fiscal_year if previous_report else None,
                title=risk.risk_summary[:120] if risk.risk_summary else "",
                category=risk.category,
                severity=risk.severity_label or str(risk.severity),
                status=status,
                classification_confidence=risk.confidence_score,
                factors=factors,
            )
            all_results.append(attach_match(
                result,
                matches_criteria(factors, request.criteria, request.logic),
            ))

    matched = [item for item in all_results if item.matched]
    matched.sort(key=lambda item: (item.overall_score, item.classification_confidence), reverse=True)
    return ScannerResponse(
        logic=request.logic,
        criteria=request.criteria,
        total_matches=len(matched),
        page=request.page,
        page_size=request.page_size,
        results=matched[(request.page - 1) * request.page_size:request.page * request.page_size],
        factor_weights=SCORE_WEIGHTS,
    )


def _reference(item, source: str) -> ScannerEvidence:
    return ScannerEvidence(
        document_id=item.document_id,
        report_year=item.report_year,
        page=item.page,
        chunk_id=item.chunk_id,
        source=source,
        excerpt=item.text_excerpt or "",
    )


def _risk_evidence(record, current_report, previous_report):
    evidence = []
    for side, item, report in (
        ("year_1", record.evidence_prev, previous_report),
        ("year_2", record.evidence_current, current_report),
    ):
        if item is not None:
            evidence.append(ScannerEvidence(
                document_id=item.document_id or (report.source_file if report else None),
                source_url=(item.metadata or {}).get("source_url"),
                report_year=item.report_year or (report.fiscal_year if report else None),
                page=item.page,
                chunk_id=item.chunk_id,
                source=f"Phase 2 risk evidence ({side})",
                excerpt=item.text[:500],
            ))
    return evidence


def _risk_evidence_from_item(risk, report):
    return [ScannerEvidence(
        document_id=report.source_file,
        source_url=(risk.extra_metadata or {}).get("source_url") or report.source_url,
        report_year=report.fiscal_year,
        page=risk.source_page,
        source="risk_items.source_paragraph" if risk.source_paragraph else "risk_items.summary",
        excerpt=(risk.source_paragraph or risk.summary)[:500],
    )]


def _build_factors(
    *, risk, current_risk, previous_risk, record, explanation, financial_analysis,
    market, industry, evidence, status,
) -> list[ContributingFactor]:
    confidence_evidence = evidence
    if record is not None and explanation is not None:
        evolution_evidence = [_reference(item, "Phase 2 explainability") for item in explanation.supporting_evidence]
    else:
        evolution_evidence = []
    severity = risk.severity_label or str(risk.severity)
    severity_score = SEVERITY_SCORES.get(severity.upper(), 0.5)
    severity_text = (
        f"Stored classification is {severity.lower()} (deterministic scale score {severity_score:.2f})."
        if severity.upper() in SEVERITY_SCORES
        else f"Stored severity '{risk.severity}' is outside the known scale; a neutral score is used."
    )
    factors = [
        ContributingFactor(
            factor="category", label="Risk category", observed=True, value=risk.category,
            score=None, explanation="Stored Phase 1 risk taxonomy classification.", evidence=evidence,
        ),
        ContributingFactor(
            factor="severity", label="Severity", observed=True, value=severity,
            score=severity_score, explanation=severity_text, evidence=evidence,
        ),
        ContributingFactor(
            factor="status", label="Evolution status", observed=True, value=status,
            score=STATUS_SCORES.get(status),
            explanation=(
                f"Phase 2 classified the disclosure as {status}; this describes disclosure change "
                "and does not by itself establish a change in realized business risk."
                if record is not None else "No earlier report pair was available for Phase 2 evolution comparison."
            ),
            evidence=evolution_evidence,
        ),
    ]

    correlations = []
    if financial_analysis is not None and record is not None:
        pair_ids = {record.year_1_risk_id, record.year_2_risk_id}
        correlations = [
            item for item in financial_analysis.correlations
            if item.risk_item_id_prev in pair_ids or item.risk_item_id_current in pair_ids
        ]
    financial_observed = bool(correlations)
    directions = [
        _financial_direction(item.metric_name, item.metric_direction)
        for item in correlations
    ]
    financial_value = (
        "ADVERSE" if "ADVERSE" in directions else "FAVORABLE" if directions and all(d == "FAVORABLE" for d in directions)
        else "MIXED" if directions else "UNAVAILABLE"
    )
    financial_score = (
        0.8 if financial_value == "ADVERSE" else 0.25 if financial_value == "FAVORABLE"
        else 0.5 if financial_value == "MIXED" else None
    )
    financial_evidence = [
        _reference(ref, "Phase 2 financial analysis")
        for item in correlations for ref in item.supporting_evidence
    ]
    factors.append(ContributingFactor(
        factor="financial_signal", label="Financial change", observed=financial_observed,
        value=financial_value, score=financial_score,
        explanation=(
            "; ".join(
                f"{item.metric_name} {item.metric_direction.lower()} was deterministically "
                f"mapped to {_financial_direction(item.metric_name, item.metric_direction).lower()}"
                for item in correlations
            ) + ". Existing Phase 2 links are term-based associations, not causal conclusions."
            if financial_observed else "No risk-linked financial correlation with supporting evidence was available."
        ), evidence=financial_evidence,
    ))

    related_market = [
        item for item in market.related_risks
        if record is not None and item.risk_item_id_prev == record.year_1_risk_id
        and item.risk_item_id_current == record.year_2_risk_id
    ]
    related_event_ids = {item.event_id for item in related_market}
    related_events = [item for item in market.events if item.id in related_event_ids]
    # Keep sourced company news visible to the scanner even when no deterministic
    # term overlap links it to this particular risk. In that case the event is
    # explicitly context only and contributes no risk score.
    events = related_events or (market.events if market.provider_available else [])
    market_value = (
        "RELATED" if related_events else "CONTEXT_ONLY" if events
        else "NONE" if market.provider_available else "UNAVAILABLE"
    )
    factors.append(ContributingFactor(
        factor="market_signal", label="Market signal", observed=market.provider_available,
        value=market_value,
        score=(max((item.confidence_score for item in related_market), default=0.75)
               if related_events else None),
        explanation=(
            "Market event and disclosure share supported terms; no causal relationship is inferred."
            if related_events else "Company-specific market events are included as context only; none is linked to this risk by supported term overlap."
            if events else "Provider returned no event; this is not evidence that no exposure exists."
            if market.provider_available else "Market intelligence provider is unavailable."
        ),
        evidence=[ScannerEvidence(
            document_id=event.evidence.source, report_year=event.evidence.publication_date.year if event.evidence.publication_date else None,
            source_url=str(event.evidence.source_url) if event.evidence.source_url else None,
            source="Phase 3.1 market event", excerpt=event.evidence.excerpt or event.summary or event.title,
        ) for event in events],
    ))

    assessments = [
        item for item in industry.assessments
        if record is not None and item.risk_id in {record.year_1_risk_id, record.year_2_risk_id}
    ]
    risk_categories = {risk.category.casefold()}
    if current_risk is not None:
        risk_categories.add(current_risk.category.casefold())
    if previous_risk is not None:
        risk_categories.add(previous_risk.category.casefold())
    peer_comparisons = [
        item for item in industry.peer_comparisons
        if record is not None and item.category.casefold() in risk_categories
    ]
    industry_classifications = [item.classification for item in assessments]
    industry_value = (
        "UNAVAILABLE" if not industry.provider_available
        else "INDUSTRY_WIDE" if "INDUSTRY_WIDE" in industry_classifications
        else "COMPANY_SPECIFIC" if "COMPANY_SPECIFIC" in industry_classifications
        else "PEER_OBSERVED" if peer_comparisons
        else "UNCLASSIFIED" if industry_classifications
        else "NONE"
    )
    theme_ids = {theme_id for item in assessments for theme_id in item.supporting_themes}
    themes = [item for item in industry.themes if item.id in theme_ids]
    factors.append(ContributingFactor(
        factor="industry_signal", label="Industry signal", observed=industry.provider_available,
        value=industry_value,
        score=(0.75 if industry_value == "INDUSTRY_WIDE" else 0.5 if industry_value in {"COMPANY_SPECIFIC", "UNCLASSIFIED", "PEER_OBSERVED"} else 0.0 if industry.provider_available else None),
        explanation=(
            "Industry theme overlaps the risk under the existing Phase 3.2 classifier; no causation is inferred."
            if themes else "No related industry theme was returned; this does not establish absence of industry risk."
            if not peer_comparisons and industry.provider_available else
            "A sourced peer filing reports this category; evidence is peer-observed and does not establish an industry-wide theme."
            if peer_comparisons else "Industry intelligence provider is unavailable."
        ),
        evidence=[ScannerEvidence(
            document_id=theme.evidence.source, report_year=theme.evidence.publication_date.year if theme.evidence.publication_date else None,
            source_url=str(theme.evidence.source_url) if theme.evidence.source_url else None,
            source="Phase 3.2 industry theme", excerpt=theme.evidence.excerpt or theme.name,
        ) for theme in themes] + [ScannerEvidence(
            document_id=item.source,
            report_year=item.publication_date.year if item.publication_date else None,
            source_url=str(item.source_url) if item.source_url else None,
            source="Phase 3.2 peer filing",
            excerpt=item.excerpt or "",
        ) for comparison in peer_comparisons for item in comparison.evidence],
    ))

    provenance_count = sum(
        sum(bool(value) for value in (item.document_id, item.page, item.chunk_id, item.excerpt)) / 4
        for item in confidence_evidence
    )
    evidence_quality = provenance_count / len(confidence_evidence) if confidence_evidence else 0.0
    factors.extend([
        ContributingFactor(
            factor="evidence_quality", label="Evidence provenance", observed=True,
            value=round(evidence_quality, 4), score=evidence_quality,
            explanation=(
                "Provenance score is the fraction of available document, page, chunk, and source-text fields across linked risk evidence."
                if confidence_evidence else "No source document, page, chunk, or excerpt was available."
            ), evidence=confidence_evidence,
        ),
        ContributingFactor(
            factor="classification_confidence", label="Classification confidence", observed=True,
            value=risk.confidence_score, score=risk.confidence_score,
            explanation="Stored Phase 1/2 risk classification confidence; it is not a probability of loss.",
            evidence=confidence_evidence,
        ),
    ])
    return factors


def _financial_direction(metric_name: str, direction: str) -> str:
    metric = metric_name.casefold().replace(" ", "_")
    adverse_when_increased = {"debt", "total_liabilities", "debt_equity", "credit_losses", "loan_loss"}
    adverse_when_decreased = {"revenue", "net_income", "profit", "cash_and_equivalents", "deposits", "roe"}
    if metric in adverse_when_increased:
        return "ADVERSE" if direction == "INCREASED" else "FAVORABLE" if direction == "DECREASED" else "MIXED"
    if metric in adverse_when_decreased:
        return "ADVERSE" if direction == "DECREASED" else "FAVORABLE" if direction == "INCREASED" else "MIXED"
    return "MIXED"

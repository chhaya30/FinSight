from pathlib import Path

from app.comparison.evolution import RiskEvolutionClassifier
from app.comparison.explainability import ExplainabilityService
from app.comparison.matcher import SemanticRiskMatcher
from app.comparison.normalizer import RiskNormalizer
from app.config.settings import get_settings
from app.intelligence.financial_health import FinancialHealthService, FinancialSnapshotExtractor
from app.models.financial_health import FinancialHealthAnalysis
from app.db.base import FinancialSnapshot
from sqlalchemy.ext.asyncio import AsyncSession


async def load_phase2_records(
    previous_report, current_report, previous_risks, current_risks, include_financial=True, session: AsyncSession | None = None
):
    previous_normalized = [
        _normalize_risk(risk, previous_report) for risk in previous_risks
    ]
    current_normalized = [_normalize_risk(risk, current_report) for risk in current_risks]
    matches = await SemanticRiskMatcher().match_all_risks(
        current_normalized,
        previous_normalized,
        y2_year=current_report.fiscal_year,
        y1_year=previous_report.fiscal_year,
    )
    records = RiskEvolutionClassifier().classify_evolution(
        current_normalized,
        previous_normalized,
        matches,
        y2_year=current_report.fiscal_year,
        y1_year=previous_report.fiscal_year,
    )
    explanations = ExplainabilityService().explain_records(records)
    financial = (
        _load_financial_analysis(previous_report, current_report, records, session)
        if include_financial
        else None
    )
    return records, explanations, financial


def _normalize_risk(risk, report):
    risk_metadata = risk.extra_metadata or {}
    return RiskNormalizer().normalize(
        {
            "risk_id": str(risk.id),
            "report_id": str(report.id),
            "report_year": report.fiscal_year,
            "category": risk.category,
            "title": risk.risk_summary[:120] if risk.risk_summary else "",
            "summary": risk.risk_summary or "",
            "severity": risk.severity_label or str(risk.severity),
            "source_page": risk.source_page,
            "evidence": {
                "document_id": report.source_file,
                "report_year": report.fiscal_year,
                "page": risk.source_page,
                "text": risk.source_paragraph or risk.risk_summary or "",
                "metadata": {
                    "source_url": risk_metadata.get("source_url") or report.source_url,
                    "source_name": risk_metadata.get("source_name"),
                },
            },
        },
        report.fiscal_year,
    )


def _load_financial_analysis(
    previous_report, current_report, records, session: AsyncSession | None = None
) -> FinancialHealthAnalysis | None:
    settings = get_settings()
    previous_path = Path(settings.UPLOAD_DIR) / previous_report.source_file
    current_path = Path(settings.UPLOAD_DIR) / current_report.source_file
    if not previous_path.exists() or not current_path.exists():
        return None
    from app.ingestion import create_adaptive_fallback_router

    extractor = FinancialSnapshotExtractor()
    router = create_adaptive_fallback_router()
    previous_doc = router.process(previous_path)
    current_doc = router.process(current_path)
    previous_snapshot = extractor.extract(
        [page.text for page in previous_doc.pages],
        previous_report.fiscal_year,
        previous_report.source_file,
        report_id=str(previous_report.id),
    )
    current_snapshot = extractor.extract(
        [page.text for page in current_doc.pages],
        current_report.fiscal_year,
        current_report.source_file,
        report_id=str(current_report.id),
    )
    
    # Save snapshots to database if session provided
    if session:
        metric_map = {
            "revenue": "revenue",
            "net_income": "profit",
            "total_assets": "total_assets",
            "total_liabilities": "total_liabilities",
            "cash_and_equivalents": "cash_flow",
            "debt": "total_debt",
            "market_cap": "market_cap",
            "eps": "eps",
            "roe": "roe",
        }
        for snapshot, report in [(previous_snapshot, previous_report), (current_snapshot, current_report)]:
            orm_snapshot = FinancialSnapshot(
                company_id=report.company_id,
                fiscal_year=snapshot.report_year,
                currency="INR",
                data_source="pdf_extraction",
                extra_metadata={"document_id": snapshot.document_id},
            )
            for metric in snapshot.metrics.values():
                orm_field = metric_map.get(metric.metric_name)
                if orm_field and metric.value is not None:
                    setattr(orm_snapshot, orm_field, metric.value)
            
            # Calculate net_margin if revenue and profit available
            if orm_snapshot.revenue and orm_snapshot.profit and orm_snapshot.revenue != 0:
                orm_snapshot.net_margin = round(orm_snapshot.profit / orm_snapshot.revenue * 100, 2)
            
            # Calculate debt_equity if total_debt and total_assets available
            if orm_snapshot.total_debt and orm_snapshot.total_assets and orm_snapshot.total_assets != 0:
                equity = orm_snapshot.total_assets - orm_snapshot.total_debt
                if equity != 0:
                    orm_snapshot.debt_equity = round(orm_snapshot.total_debt / equity, 2)
            
            session.add(orm_snapshot)
    
    return FinancialHealthService().analyze(current_snapshot, previous_snapshot, records)

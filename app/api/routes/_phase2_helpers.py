from pathlib import Path

from app.comparison.evolution import RiskEvolutionClassifier
from app.comparison.explainability import ExplainabilityService
from app.comparison.matcher import SemanticRiskMatcher
from app.comparison.normalizer import RiskNormalizer
from app.config.settings import get_settings
from app.intelligence.financial_health import FinancialHealthService, FinancialSnapshotExtractor
from app.models.financial_health import FinancialHealthAnalysis


async def load_phase2_records(
    previous_report, current_report, previous_risks, current_risks, include_financial=True
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
        _load_financial_analysis(previous_report, current_report, records)
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
            "title": risk.summary[:120],
            "summary": risk.summary,
            "severity": risk.severity,
            "source_page": risk.source_page,
            "evidence": {
                "document_id": report.source_file,
                "report_year": report.fiscal_year,
                "page": risk.source_page,
                "text": risk.source_paragraph or risk.summary,
                "metadata": {
                    "source_url": risk_metadata.get("source_url") or report.source_url,
                    "source_name": risk_metadata.get("source_name"),
                },
            },
        },
        report.fiscal_year,
    )


def _load_financial_analysis(
    previous_report, current_report, records
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
    return FinancialHealthService().analyze(current_snapshot, previous_snapshot, records)

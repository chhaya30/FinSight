from uuid import uuid4

import pytest
from app.api.routes.dashboard import get_executive_dashboard
from app.db.base import Company, Report, RiskItem
from app.intelligence.dashboard import ExecutiveDashboardService
from app.models.comparison import AttributeChange, EvolutionChangeType, RiskEvolutionRecord
from app.models.dashboard import DashboardCompany, DashboardReport
from app.models.explainability import (
    AttributeDifference,
    EvidenceReference,
    ExplainabilityClaim,
    ExplainableRiskEvolution,
)
from app.models.financial_health import (
    FinancialHealthAnalysis,
    FinancialMetricChange,
    FinancialMetricValue,
    FinancialSnapshot,
)
from app.models.risk import RiskEvidence


def record(status: EvolutionChangeType, index: int) -> RiskEvolutionRecord:
    return RiskEvolutionRecord(
        year_1_risk_id=f"y1-{index}" if status != EvolutionChangeType.NEW else None,
        year_2_risk_id=f"y2-{index}" if status != EvolutionChangeType.REMOVED else None,
        report_id_prev="report-2024" if status != EvolutionChangeType.NEW else None,
        report_id_current="report-2025" if status != EvolutionChangeType.REMOVED else None,
        report_year_prev=2024 if status != EvolutionChangeType.NEW else None,
        report_year_current=2025 if status != EvolutionChangeType.REMOVED else None,
        change_type=status,
        match_confidence=0.9,
        semantic_similarity=0.8,
        severity_prev="High",
        severity_current="Critical",
        changed_attributes=(
            {"severity": AttributeChange(before="High", after="Critical")}
            if status == EvolutionChangeType.ESCALATED
            else {}
        ),
        evidence_prev=RiskEvidence(
            document_id="doc-2024", report_year=2024, page=10, text="Previous"
        ),
        evidence_current=RiskEvidence(
            document_id="doc-2025", report_year=2025, page=11, text="Current"
        ),
        metadata={
            "title_y1": f"Risk {index}",
            "title_y2": f"Risk {index}",
            "category": "Financial",
        },
    )


def explanation(item: RiskEvolutionRecord) -> ExplainableRiskEvolution:
    references = [
        EvidenceReference(side="year_1", document_id="doc-2024", report_year=2024, page=10),
        EvidenceReference(side="year_2", document_id="doc-2025", report_year=2025, page=11),
    ]
    return ExplainableRiskEvolution(
        year_1_risk_id=item.year_1_risk_id,
        year_2_risk_id=item.year_2_risk_id,
        change_type=item.change_type,
        what_changed=[AttributeDifference(name="severity", before="High", after="Critical")],
        why_it_matters=ExplainabilityClaim(text="Evidence-backed change.", evidence=references),
        executive_summary=ExplainabilityClaim(text="Executive change.", evidence=references),
        business_impact=ExplainabilityClaim(text="Business impact.", evidence=references),
        confidence_score=0.8,
        confidence_reason="Phase 2.1 confidence",
        supporting_evidence=references,
        source_record=item,
    )


def test_dashboard_aggregates_statuses_and_integrates_outputs():
    records = [record(status, index) for index, status in enumerate(EvolutionChangeType)]
    explanations = [explanation(item) for item in records]
    dashboard = ExecutiveDashboardService().build(
        company=DashboardCompany(id=str(uuid4()), name="JPMorgan"),
        previous_report=DashboardReport(year=2024, report_id="report-2024", source_file="2024.pdf"),
        current_report=DashboardReport(year=2025, report_id="report-2025", source_file="2025.pdf"),
        total_previous=6,
        total_current=6,
        records=records,
        explanations=explanations,
    )

    assert len(dashboard.key_risk_changes) == 6
    assert dashboard.risk_counts_by_status == {status.value: 1 for status in EvolutionChangeType}
    assert dashboard.key_risk_changes[0].why_it_matters.text
    assert dashboard.key_risk_changes[0].evidence[0].document_id == "doc-2024"
    assert dashboard.executive_summary.evidence


def test_dashboard_financial_integration_preserves_changes_and_evidence():
    current_metric = FinancialMetricValue(
        metric_name="revenue",
        value=110,
        report_year=2025,
        document_id="doc-2025",
        page=2,
        source_text="Revenue 110",
    )
    change = FinancialMetricChange(
        metric_name="revenue",
        report_year_prev=2024,
        report_year_current=2025,
        previous_value=100,
        current_value=110,
        absolute_change=10,
        percent_change=10,
        direction="INCREASED",
        supporting_evidence=[
            EvidenceReference(side="year_2", document_id="doc-2025", report_year=2025, page=2)
        ],
    )
    financial = FinancialHealthAnalysis(
        snapshot_current=FinancialSnapshot(
            report_year=2025,
            document_id="doc-2025",
            metrics={"revenue": current_metric},
        ),
        changes=[change],
    )
    dashboard = ExecutiveDashboardService().build(
        company=DashboardCompany(id=str(uuid4()), name="JPMorgan"),
        previous_report=DashboardReport(year=2024, report_id="report-2024", source_file="2024.pdf"),
        current_report=DashboardReport(year=2025, report_id="report-2025", source_file="2025.pdf"),
        total_previous=0,
        total_current=0,
        records=[],
        explanations=[],
        financial=financial,
    )

    assert dashboard.financial_metrics[0].value == 110
    assert dashboard.financial_changes[0].direction == "INCREASED"
    assert dashboard.financial_changes[0].supporting_evidence[0].page == 2
    assert dashboard.risk_financial_correlations == []


def test_dashboard_handles_empty_data_without_fabricating_values():
    dashboard = ExecutiveDashboardService().build(
        company=DashboardCompany(id=str(uuid4()), name="Empty Company"),
        previous_report=DashboardReport(year=2024, report_id="report-2024", source_file="2024.pdf"),
        current_report=DashboardReport(year=2025, report_id="report-2025", source_file="2025.pdf"),
        total_previous=0,
        total_current=0,
        records=[],
        explanations=[],
    )

    assert dashboard.key_risk_changes == []
    assert dashboard.financial_metrics == []
    assert dashboard.financial_changes == []
    assert dashboard.risk_counts_by_status == {status.value: 0 for status in EvolutionChangeType}
    assert dashboard.evidence == []


@pytest.mark.asyncio
async def test_dashboard_get_endpoint_returns_db_backed_response(db_session):
    company = Company(name="Dashboard Company", sector="Banking")
    db_session.add(company)
    await db_session.flush()
    previous = Report(
        company_id=company.id,
        fiscal_year=2024,
        source_file="missing-2024.pdf",
        processing_status="completed",
    )
    current = Report(
        company_id=company.id,
        fiscal_year=2025,
        source_file="missing-2025.pdf",
        processing_status="completed",
    )
    db_session.add_all([previous, current])
    await db_session.flush()
    db_session.add_all(
        [
            RiskItem(
                report_id=previous.id,
                category="Financial",
                severity="High",
                confidence_score=0.8,
                summary="Debt refinancing risk",
                source_page=10,
                source_paragraph="Previous debt disclosure",
            ),
            RiskItem(
                report_id=current.id,
                category="Financial",
                severity="High",
                confidence_score=0.8,
                summary="Debt refinancing risk",
                source_page=11,
                source_paragraph="Current debt disclosure",
            ),
        ]
    )
    await db_session.flush()

    response = await get_executive_dashboard(company.id, 2025, 2024, db_session)

    assert response.total_risks_previous == 1
    assert response.total_risks_current == 1
    assert sum(response.risk_counts_by_status.values()) == 1
    assert response.key_risk_changes[0].evidence
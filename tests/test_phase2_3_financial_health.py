import math
from uuid import uuid4

import pytest
from app.api.routes.financial_health import analyze_financial_health
from app.intelligence.financial_health import FinancialHealthService, FinancialSnapshotExtractor
from app.models.comparison import EvolutionChangeType, RiskEvolutionRecord
from app.models.financial_health import (
    FinancialHealthRequest,
    FinancialMetricValue,
    FinancialSnapshot,
)
from app.models.risk import RiskEvidence


def metric(name: str, value: float | None, year: int, page: int = 2) -> FinancialMetricValue:
    return FinancialMetricValue(
        metric_name=name,
        value=value,
        report_year=year,
        document_id=f"report-{year}",
        page=page,
        source_text=f"{name} {value}",
    )


def snapshot(year: int, metrics: dict[str, FinancialMetricValue]) -> FinancialSnapshot:
    return FinancialSnapshot(
        company_id=uuid4(),
        report_id=f"report-{year}",
        report_year=year,
        document_id=f"report-{year}",
        metrics=metrics,
    )


def test_extracts_labelled_financial_values_with_page_provenance():
    pages = [
        "Cover page",
        "Financial Highlights As of or for the year ended December 31, (in millions) "
        "2024 2023 Total net revenue $ 177,556 $ 158,104 Net income $ 58,471 $ 49,552 "
        "Total assets 4,002,814 3,875,393",
    ]

    result = FinancialSnapshotExtractor().extract(pages, 2024, "jpm-2024")

    assert result.metrics["revenue"].value == 177556
    assert result.metrics["net_income"].value == 58471
    assert result.metrics["total_assets"].value == 4002814
    assert all(
        item.document_id == "jpm-2024" and item.page == 2
        for item in result.metrics.values()
    )


def test_calculates_yoy_changes_and_percentages_deterministically():
    previous = snapshot(2024, {"revenue": metric("revenue", 100, 2024)})
    current = snapshot(2025, {"revenue": metric("revenue", 125, 2025)})

    change = FinancialHealthService().calculate_changes(previous, current)[0]

    assert change.absolute_change == 25
    assert change.percent_change == 25
    assert change.direction == "INCREASED"
    assert {(item.document_id, item.page) for item in change.supporting_evidence} == {
        ("report-2024", 2),
        ("report-2025", 2),
    }


def test_missing_and_invalid_values_are_unavailable_not_invented():
    previous = snapshot(
        2024,
        {"revenue": metric("revenue", 0, 2024), "debt": metric("debt", math.nan, 2024)},
    )
    current = snapshot(2025, {"revenue": metric("revenue", 100, 2025)})

    changes = FinancialHealthService().calculate_changes(previous, current)

    by_name = {change.metric_name: change for change in changes}
    assert by_name["revenue"].direction == "INCREASED"
    assert by_name["revenue"].percent_change is None
    assert by_name["debt"].direction == "UNAVAILABLE"
    assert by_name["debt"].absolute_change is None


def test_correlates_relevant_metric_without_claiming_causation():
    previous = snapshot(2024, {"debt": metric("debt", 100, 2024)})
    current = snapshot(2025, {"debt": metric("debt", 120, 2025)})
    record = RiskEvolutionRecord(
        year_1_risk_id="risk-2024",
        year_2_risk_id="risk-2025",
        change_type=EvolutionChangeType.MODIFIED,
        match_confidence=0.9,
        semantic_similarity=0.8,
        metadata={"title_y1": "Debt refinancing pressure", "title_y2": "Debt refinancing pressure"},
        evidence_prev=RiskEvidence(
            document_id="risk-doc-2024", report_year=2024, page=40, text="Debt risk"
        ),
        evidence_current=RiskEvidence(
            document_id="risk-doc-2025", report_year=2025, page=44, text="Debt risk"
        ),
    )

    result = FinancialHealthService().analyze(current, previous, [record])

    assert len(result.correlations) == 1
    correlation = result.correlations[0]
    assert correlation.metric_name == "debt"
    assert correlation.metric_direction == "INCREASED"
    assert correlation.relationship == "ASSOCIATED_DISCLOSURE_OVERLAP"
    assert "not a causal conclusion" in correlation.explanation
    assert {(item.document_id, item.page) for item in correlation.supporting_evidence} == {
        ("report-2024", 2),
        ("report-2025", 2),
        ("risk-doc-2024", 40),
        ("risk-doc-2025", 44),
    }


def test_unrelated_risk_does_not_create_financial_correlation():
    previous = snapshot(2024, {"revenue": metric("revenue", 100, 2024)})
    current = snapshot(2025, {"revenue": metric("revenue", 90, 2025)})
    record = RiskEvolutionRecord(
        year_2_risk_id="risk-2025",
        change_type=EvolutionChangeType.NEW,
        evidence_current=RiskEvidence(
            document_id="risk-doc-2025", report_year=2025, page=9, text="Cyber risk"
        ),
        metadata={"title": "Cybersecurity incident response"},
    )

    result = FinancialHealthService().analyze(current, previous, [record])

    assert result.correlations == []


@pytest.mark.asyncio
async def test_financial_health_api_returns_analysis():
    previous = snapshot(2024, {"revenue": metric("revenue", 100, 2024)})
    current = snapshot(2025, {"revenue": metric("revenue", 110, 2025)})

    response = await analyze_financial_health(
        FinancialHealthRequest(snapshot_previous=previous, snapshot_current=current)
    )

    assert response.changes[0].direction == "INCREASED"
    assert response.changes[0].supporting_evidence[0].page == 2
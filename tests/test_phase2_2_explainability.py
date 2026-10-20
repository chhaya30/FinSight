import pytest
from app.api.routes.explainability import explain_evolution
from app.comparison.explainability import ExplainabilityService
from app.models.comparison import AttributeChange, EvolutionChangeType, RiskEvolutionRecord
from app.models.explainability import ExplainabilityRequest
from app.models.risk import RiskEvidence


def make_record(
    change_type: EvolutionChangeType, with_evidence: bool = True
) -> RiskEvolutionRecord:
    evidence_prev = (
        RiskEvidence(
            document_id="jpm-2024",
            report_year=2024,
            page=101,
            chunk_id="chunk-y1",
            text="Year 1 disclosure text.",
        )
        if with_evidence
        else None
    )
    evidence_current = (
        RiskEvidence(
            document_id="jpm-2025",
            report_year=2025,
            page=115,
            chunk_id="chunk-y2",
            text="Year 2 disclosure text.",
        )
        if with_evidence
        else None
    )
    return RiskEvolutionRecord(
        year_1_risk_id=None if change_type == EvolutionChangeType.NEW else "y1-risk",
        year_2_risk_id=None if change_type == EvolutionChangeType.REMOVED else "y2-risk",
        report_id_prev="jpm-2024" if change_type != EvolutionChangeType.NEW else None,
        report_id_current="jpm-2025" if change_type != EvolutionChangeType.REMOVED else None,
        report_year_prev=2024 if change_type != EvolutionChangeType.NEW else None,
        report_year_current=2025 if change_type != EvolutionChangeType.REMOVED else None,
        change_type=change_type,
        match_confidence=0.91,
        semantic_similarity=0.87,
        severity_prev="High",
        severity_current="Critical",
        changed_attributes=(
            {"severity": AttributeChange(before="High", after="Critical")}
            if change_type == EvolutionChangeType.ESCALATED
            else {"severity": AttributeChange(before="Critical", after="High")}
            if change_type == EvolutionChangeType.DE_ESCALATED
            else {"title": AttributeChange(before="Old title", after="Updated title")}
            if change_type == EvolutionChangeType.MODIFIED
            else {}
        ),
        evidence_prev=evidence_prev,
        evidence_current=evidence_current,
    )


def test_all_six_statuses_produce_explainable_outputs():
    statuses = list(EvolutionChangeType)
    explanations = ExplainabilityService().explain_records(
        [make_record(status) for status in statuses]
    )

    assert [item.change_type for item in explanations] == statuses
    for item in explanations:
        assert item.what_changed or item.change_type == EvolutionChangeType.UNCHANGED
        assert item.why_it_matters.text
        assert item.executive_summary.text
        assert item.business_impact.text
        assert item.confidence_reason
        assert item.supporting_evidence
        assert item.why_it_matters.evidence == item.supporting_evidence
        assert item.executive_summary.evidence == item.supporting_evidence
        assert item.business_impact.evidence == item.supporting_evidence


def test_structured_differences_and_source_references_are_preserved():
    result = ExplainabilityService().explain_record(
        make_record(EvolutionChangeType.ESCALATED)
    )

    assert result.what_changed[0].name == "severity"
    assert result.what_changed[0].before == "High"
    assert result.what_changed[0].after == "Critical"
    assert {
        (item.document_id, item.page, item.chunk_id) for item in result.supporting_evidence
    } == {
        ("jpm-2024", 101, "chunk-y1"),
        ("jpm-2025", 115, "chunk-y2"),
    }
    assert result.source_record == make_record(EvolutionChangeType.ESCALATED)


def test_new_and_removed_have_deterministic_presence_differences():
    service = ExplainabilityService()
    new_result = service.explain_record(make_record(EvolutionChangeType.NEW))
    removed_result = service.explain_record(make_record(EvolutionChangeType.REMOVED))

    assert new_result.what_changed[-1].name == "risk_presence"
    assert (new_result.what_changed[-1].before, new_result.what_changed[-1].after) == (False, True)
    assert removed_result.what_changed[-1].name == "risk_presence"
    assert (
        removed_result.what_changed[-1].before,
        removed_result.what_changed[-1].after,
    ) == (True, False)


def test_missing_evidence_never_receives_invented_confidence_or_citation():
    result = ExplainabilityService().explain_record(
        make_record(EvolutionChangeType.MODIFIED, with_evidence=False)
    )

    assert result.supporting_evidence == []
    assert result.confidence_score == 0
    assert "No Year-1 or Year-2 evidence" in result.confidence_reason
    assert "unsupported business outcome" in result.business_impact.text
    assert result.why_it_matters.evidence == []


def test_incomplete_evidence_is_not_promoted_to_a_citation():
    record = make_record(EvolutionChangeType.MODIFIED)
    record.evidence_current = RiskEvidence(text="Text without document or page")

    result = ExplainabilityService().explain_record(record)

    assert len(result.supporting_evidence) == 1
    assert result.supporting_evidence[0].side == "year_1"
    assert result.confidence_score == 0.0


@pytest.mark.asyncio
async def test_explainability_api_returns_one_output_per_record():
    request = ExplainabilityRequest(
        records=[make_record(EvolutionChangeType.NEW), make_record(EvolutionChangeType.REMOVED)]
    )

    response = await explain_evolution(request)

    assert len(response.explanations) == 2
    assert [item.change_type for item in response.explanations] == [
        EvolutionChangeType.NEW,
        EvolutionChangeType.REMOVED,
    ]
from collections import Counter

from app.models.comparison import EvolutionChangeType, RiskEvolutionRecord
from app.models.dashboard import (
    DashboardCompany,
    DashboardReport,
    DashboardRiskChange,
    ExecutiveDashboardResponse,
)
from app.models.explainability import (
    EvidenceReference,
    ExplainabilityClaim,
    ExplainableRiskEvolution,
)
from app.models.financial_health import FinancialHealthAnalysis


class ExecutiveDashboardService:
    """Compose Phase 2.1, 2.2, and 2.3 outputs without reimplementing them."""

    def build(
        self,
        company: DashboardCompany,
        previous_report: DashboardReport,
        current_report: DashboardReport,
        total_previous: int,
        total_current: int,
        records: list[RiskEvolutionRecord],
        explanations: list[ExplainableRiskEvolution],
        financial: FinancialHealthAnalysis | None = None,
    ) -> ExecutiveDashboardResponse:
        counts = Counter(record.change_type.value for record in records)
        status_counts = {
            status.value: counts.get(status.value, 0) for status in EvolutionChangeType
        }
        explanation_by_key = {
            (item.year_1_risk_id, item.year_2_risk_id): item for item in explanations
        }
        key_changes = [
            self._risk_change(
                record,
                explanation_by_key.get((record.year_1_risk_id, record.year_2_risk_id)),
            )
            for record in records
        ]
        evidence = self._unique_evidence(
            reference
            for item in explanations
            for reference in item.supporting_evidence
        )
        executive_summary = self._summary_claim(status_counts, explanations)
        business_impact = self._business_impact_claim(financial, explanations)

        return ExecutiveDashboardResponse(
            company=company,
            reports=[previous_report, current_report],
            total_risks_previous=total_previous,
            total_risks_current=total_current,
            risk_counts_by_status=status_counts,
            key_risk_changes=key_changes,
            executive_summary=executive_summary,
            business_impact=business_impact,
            financial_metrics=(
                list(financial.snapshot_current.metrics.values()) if financial else []
            ),
            financial_changes=financial.changes if financial else [],
            risk_financial_correlations=financial.correlations if financial else [],
            evidence=evidence,
            source_records=records,
        )

    @staticmethod
    def _risk_change(
        record: RiskEvolutionRecord,
        explanation: ExplainableRiskEvolution | None,
    ) -> DashboardRiskChange:
        metadata = record.metadata
        title = metadata.get("title_y2") or metadata.get("title_y1") or metadata.get("title")
        category = metadata.get("category")
        return DashboardRiskChange(
            year_1_risk_id=record.year_1_risk_id,
            year_2_risk_id=record.year_2_risk_id,
            title=title,
            category=category,
            severity_previous=record.severity_prev,
            severity_current=record.severity_current,
            change_type=record.change_type,
            what_changed=explanation.what_changed if explanation else [],
            why_it_matters=(
                explanation.why_it_matters
                if explanation
                else ExplainabilityClaim(
                    text="No explainability output is available for this record.", evidence=[]
                )
            ),
            confidence=explanation.confidence_score if explanation else 0.0,
            evidence=explanation.supporting_evidence if explanation else [],
        )

    @classmethod
    def _summary_claim(
        cls,
        counts: dict[str, int],
        explanations: list[ExplainableRiskEvolution],
    ) -> ExplainabilityClaim:
        text = (
            f"Risk evolution contains {counts.get('NEW', 0)} new, "
            f"{counts.get('REMOVED', 0)} removed, "
            f"{counts.get('ESCALATED', 0)} escalated, and "
            f"{counts.get('MODIFIED', 0)} modified disclosures."
        )
        evidence = cls._unique_evidence(
            reference
            for item in explanations
            for reference in item.executive_summary.evidence
        )
        return ExplainabilityClaim(text=text, evidence=evidence)

    @classmethod
    def _business_impact_claim(
        cls,
        financial: FinancialHealthAnalysis | None,
        explanations: list[ExplainableRiskEvolution],
    ) -> ExplainabilityClaim:
        correlation_count = len(financial.correlations) if financial else 0
        text = (
            f"{correlation_count} evidence-supported risk and financial disclosure "
            "associations are available; no causal conclusion is inferred."
        )
        evidence = cls._unique_evidence(
            reference
            for item in explanations
            for reference in item.business_impact.evidence
        )
        if financial:
            evidence = cls._unique_evidence(
                [
                    *evidence,
                    *(
                        item
                        for change in financial.changes
                        for item in change.supporting_evidence
                    ),
                ]
            )
        return ExplainabilityClaim(text=text, evidence=evidence)

    @staticmethod
    def _unique_evidence(references) -> list[EvidenceReference]:
        unique: dict[tuple[str, str, int, str | None], EvidenceReference] = {}
        for reference in references:
            key = (reference.side, reference.document_id, reference.page, reference.chunk_id)
            unique[key] = reference
        return list(unique.values())
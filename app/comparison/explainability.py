from app.models.comparison import EvolutionChangeType, RiskEvolutionRecord
from app.models.explainability import (
    AttributeDifference,
    EvidenceReference,
    ExplainabilityClaim,
    ExplainableRiskEvolution,
)


class ExplainabilityService:
    """Build evidence-grounded Phase 2.2 explanations without unsupported inference."""

    def explain_records(
        self, records: list[RiskEvolutionRecord]
    ) -> list[ExplainableRiskEvolution]:
        return [self.explain_record(record) for record in records]

    def explain_record(self, record: RiskEvolutionRecord) -> ExplainableRiskEvolution:
        evidence = self._evidence_for(record)
        differences = [
            AttributeDifference(name=name, before=change.before, after=change.after)
            for name, change in record.changed_attributes.items()
        ]
        differences = self._add_unmatched_difference(record, differences)
        status = record.change_type.value
        evidence_text = self._evidence_label(evidence)

        if status == EvolutionChangeType.NEW.value:
            change_text = "Risk appears in Year 2 with no matched Year 1 risk."
        elif status == EvolutionChangeType.REMOVED.value:
            change_text = "Risk appears in Year 1 with no matched Year 2 risk."
        elif status == EvolutionChangeType.UNCHANGED.value:
            change_text = "No recorded structured or disclosure change was detected."
        else:
            change_text = self._changed_text(differences, status)

        claim_evidence = evidence
        why_text = f"{change_text} Classification: {status}. Source: {evidence_text}."
        executive_text = f"{status}: {change_text}"
        impact_text = (
            f"The recorded change is {status.lower()} based only on the compared risk attributes "
            f"and cited disclosure evidence; no unsupported business outcome is inferred."
        )
        confidence, reason = self._confidence(record, evidence)

        return ExplainableRiskEvolution(
            year_1_risk_id=record.year_1_risk_id,
            year_2_risk_id=record.year_2_risk_id,
            report_id_prev=record.report_id_prev,
            report_id_current=record.report_id_current,
            report_year_prev=record.report_year_prev,
            report_year_current=record.report_year_current,
            change_type=record.change_type,
            what_changed=differences,
            why_it_matters=ExplainabilityClaim(text=why_text, evidence=claim_evidence),
            executive_summary=ExplainabilityClaim(text=executive_text, evidence=claim_evidence),
            business_impact=ExplainabilityClaim(text=impact_text, evidence=claim_evidence),
            confidence_score=confidence,
            confidence_reason=reason,
            supporting_evidence=evidence,
            source_record=record,
        )

    @staticmethod
    def _evidence_for(record: RiskEvolutionRecord) -> list[EvidenceReference]:
        references: list[EvidenceReference] = []
        evidence_pairs = (
            ("year_1", record.evidence_prev),
            ("year_2", record.evidence_current),
        )
        for side, evidence in evidence_pairs:
            if evidence is not None and evidence.document_id and evidence.page:
                references.append(
                    EvidenceReference(
                        side=side,
                        document_id=evidence.document_id,
                        report_year=evidence.report_year,
                        page=evidence.page,
                        chunk_id=evidence.chunk_id,
                        text_excerpt=evidence.text[:500],
                    )
                )
        return references

    @staticmethod
    def _add_unmatched_difference(
        record: RiskEvolutionRecord,
        differences: list[AttributeDifference],
    ) -> list[AttributeDifference]:
        if record.change_type == EvolutionChangeType.NEW:
            return differences + [
                AttributeDifference(name="risk_presence", before=False, after=True)
            ]
        if record.change_type == EvolutionChangeType.REMOVED:
            return differences + [
                AttributeDifference(name="risk_presence", before=True, after=False)
            ]
        return differences

    @staticmethod
    def _changed_text(differences: list[AttributeDifference], status: str) -> str:
        if not differences:
            return (
                f"A {status} classification was recorded without additional "
                "structured differences."
            )
        names = ", ".join(difference.name for difference in differences)
        return f"{status} change recorded in: {names}."

    @staticmethod
    def _evidence_label(evidence: list[EvidenceReference]) -> str:
        if not evidence:
            return "no document evidence was supplied"
        labels = [
            f"{item.document_id or 'unknown document'} page {item.page or 'unknown'}"
            for item in evidence
        ]
        return "; ".join(labels)

    @staticmethod
    def _confidence(
        record: RiskEvolutionRecord,
        evidence: list[EvidenceReference],
    ) -> tuple[float, str]:
        if not evidence:
            return 0.0, "No Year-1 or Year-2 evidence was supplied."
        if record.change_type in (EvolutionChangeType.NEW, EvolutionChangeType.REMOVED):
            return (
                1.0,
                "Unmatched status is deterministic and supported by the "
                "available side's evidence.",
            )
        if len(evidence) < 2:
            return 0.0, "Both Year-1 and Year-2 evidence are required for a comparison claim."
        score = round(min(record.match_confidence, record.semantic_similarity), 4)
        return (
            score,
            "Confidence is the lower of Phase 2.1 match confidence and "
            "semantic similarity.",
        )
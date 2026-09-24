from app.config.logging import get_logger
from app.models.comparison import (
    AttributeChange,
    EvolutionChangeType,
    EvolutionSummaryResult,
    RiskEvolutionRecord,
    RiskMatchResult,
)
from app.models.risk import NormalizedRisk

logger = get_logger(__name__)

# Explicit ordered severity scale
SEVERITY_LEVELS: dict[str, int] = {
    "INFORMATIONAL": 1,
    "LOW": 2,
    "MEDIUM": 3,
    "HIGH": 4,
    "CRITICAL": 5,
}


def parse_severity_level(severity: str | None) -> int | None:
    """Parse severity string to ordinal integer level."""
    if not severity:
        return None
    s = str(severity).strip().upper()
    return SEVERITY_LEVELS.get(s, None)


def parse_dimension_level(value: str | None) -> int | None:
    """Parse a known LOW-to-CRITICAL dimension without guessing unknown values."""
    if not value:
        return None
    return SEVERITY_LEVELS.get(str(value).strip().upper())


class RiskEvolutionClassifier:
    """Deterministic classifier for Year-over-Year risk evolution (Phase 2.1.3)."""

    def __init__(self, min_confidence_threshold: float = 0.55):
        self.min_confidence_threshold = min_confidence_threshold

    def classify_evolution(
        self,
        y2_risks: list[NormalizedRisk],
        y1_risks: list[NormalizedRisk],
        match_results: list[RiskMatchResult],
        y2_year: int = 2025,
        y1_year: int = 2024,
    ) -> list[RiskEvolutionRecord]:
        """Classify Year 1 vs Year 2 risks into NEW, REMOVED, UNCHANGED, MODIFIED, ESCALATED, DE-ESCALATED."""
        y2_map = {r.risk_id: r for r in y2_risks}
        y1_map = {r.risk_id: r for r in y1_risks}

        # Collect all candidate pairs with confidence >= threshold
        all_candidate_pairs: list[tuple[str, str, float, float]] = []
        for m_res in match_results:
            y2_id = m_res.year_2_risk_id
            for cand in m_res.candidate_matches:
                if cand.match_confidence >= self.min_confidence_threshold:
                    all_candidate_pairs.append(
                        (y2_id, cand.year_1_risk_id, cand.match_confidence, cand.semantic_similarity)
                    )

        # Sort candidate pairs greedily by match_confidence descending
        all_candidate_pairs.sort(key=lambda x: x[2], reverse=True)

        matched_y2_ids: set[str] = set()
        matched_y1_ids: set[str] = set()
        paired_records: list[RiskEvolutionRecord] = []

        # 1-to-1 Match Resolution: ensure 1-to-1 pairing
        for y2_id, y1_id, confidence, sem_sim in all_candidate_pairs:
            if y2_id not in matched_y2_ids and y1_id not in matched_y1_ids:
                matched_y2_ids.add(y2_id)
                matched_y1_ids.add(y1_id)

                y2_risk = y2_map[y2_id]
                y1_risk = y1_map[y1_id]

                rec = self._classify_matched_pair(
                    y2_risk, y1_risk, confidence, sem_sim, y2_year=y2_year, y1_year=y1_year
                )
                paired_records.append(rec)

        # Process NEW risks (Year-2 risks with no 1-to-1 match)
        new_records: list[RiskEvolutionRecord] = []
        for y2_risk in y2_risks:
            if y2_risk.risk_id not in matched_y2_ids:
                new_records.append(
                    RiskEvolutionRecord(
                        year_2_risk_id=y2_risk.risk_id,
                        report_id_current=y2_risk.report_id,
                        report_year_current=y2_year,
                        change_type=EvolutionChangeType.NEW,
                        severity_current=y2_risk.severity,
                        likelihood_current=y2_risk.likelihood,
                        impact_current=y2_risk.impact,
                        evidence_current=y2_risk.evidence,
                        metadata={"title": y2_risk.title, "category": y2_risk.category},
                    )
                )

        # Process REMOVED risks (Year-1 risks with no 1-to-1 match)
        removed_records: list[RiskEvolutionRecord] = []
        for y1_risk in y1_risks:
            if y1_risk.risk_id not in matched_y1_ids:
                removed_records.append(
                    RiskEvolutionRecord(
                        year_1_risk_id=y1_risk.risk_id,
                        report_id_prev=y1_risk.report_id,
                        report_year_prev=y1_year,
                        change_type=EvolutionChangeType.REMOVED,
                        severity_prev=y1_risk.severity,
                        likelihood_prev=y1_risk.likelihood,
                        impact_prev=y1_risk.impact,
                        evidence_prev=y1_risk.evidence,
                        metadata={"title": y1_risk.title, "category": y1_risk.category},
                    )
                )

        return paired_records + new_records + removed_records

    def _classify_matched_pair(
        self,
        y2: NormalizedRisk,
        y1: NormalizedRisk,
        confidence: float,
        sem_sim: float,
        y2_year: int,
        y1_year: int,
    ) -> RiskEvolutionRecord:
        """Apply deterministic precedence logic to classify a matched risk pair."""
        changed_attrs: dict[str, AttributeChange] = {}

        # 1. Parse structured severity levels
        sev1_lvl = parse_severity_level(y1.severity)
        sev2_lvl = parse_severity_level(y2.severity)

        sev_direction = 0  # +1 for escalation, -1 for de-escalation, 0 for neutral
        if sev1_lvl is not None and sev2_lvl is not None:
            if sev2_lvl > sev1_lvl:
                sev_direction = 1
                changed_attrs["severity"] = AttributeChange(before=y1.severity, after=y2.severity)
            elif sev2_lvl < sev1_lvl:
                sev_direction = -1
                changed_attrs["severity"] = AttributeChange(before=y1.severity, after=y2.severity)
            elif y1.severity != y2.severity:
                changed_attrs["severity"] = AttributeChange(before=y1.severity, after=y2.severity)

        # Only known ordered values can contribute a direction. Unknown or missing
        # values are retained as changes but never used to infer severity movement.
        like_direction = self._dimension_direction(
            y1.likelihood, y2.likelihood, changed_attrs, "likelihood"
        )
        imp_direction = self._dimension_direction(
            y1.impact, y2.impact, changed_attrs, "impact"
        )

        # Conflict resolution check
        directions = [d for d in [sev_direction, like_direction, imp_direction] if d != 0]
        has_conflict = len(set(directions)) > 1

        # Determine ChangeType
        if not has_conflict and (sev_direction == 1 or like_direction == 1 or imp_direction == 1):
            change_type = EvolutionChangeType.ESCALATED
        elif not has_conflict and (sev_direction == -1 or like_direction == -1 or imp_direction == -1):
            change_type = EvolutionChangeType.DE_ESCALATED
        else:
            # Check other non-severity attribute changes (title, description, category, drivers, etc.)
            if y1.category != y2.category:
                changed_attrs["category"] = AttributeChange(before=y1.category, after=y2.category)
            if y1.title != y2.title:
                changed_attrs["title"] = AttributeChange(before=y1.title, after=y2.title)
            if y1.description != y2.description:
                changed_attrs["description"] = AttributeChange(
                    before=y1.description[:100], after=y2.description[:100]
                )
            if (y1.drivers or []) != (y2.drivers or []):
                changed_attrs["drivers"] = AttributeChange(before=y1.drivers, after=y2.drivers)
            if (y1.affected_areas or []) != (y2.affected_areas or []):
                changed_attrs["affected_areas"] = AttributeChange(
                    before=y1.affected_areas, after=y2.affected_areas
                )

            if changed_attrs or has_conflict:
                change_type = EvolutionChangeType.MODIFIED
            else:
                change_type = EvolutionChangeType.UNCHANGED

        return RiskEvolutionRecord(
            year_1_risk_id=y1.risk_id,
            year_2_risk_id=y2.risk_id,
            report_id_prev=y1.report_id,
            report_id_current=y2.report_id,
            report_year_prev=y1_year,
            report_year_current=y2_year,
            change_type=change_type,
            match_confidence=round(confidence, 4),
            semantic_similarity=round(sem_sim, 4),
            severity_prev=y1.severity,
            severity_current=y2.severity,
            likelihood_prev=y1.likelihood,
            likelihood_current=y2.likelihood,
            impact_prev=y1.impact,
            impact_current=y2.impact,
            changed_attributes=changed_attrs,
            evidence_prev=y1.evidence,
            evidence_current=y2.evidence,
            metadata={"title_y1": y1.title, "title_y2": y2.title},
        )

    @staticmethod
    def _dimension_direction(
        before: str | None,
        after: str | None,
        changed_attrs: dict[str, AttributeChange],
        name: str,
    ) -> int:
        if before == after:
            return 0
        if before is not None or after is not None:
            changed_attrs[name] = AttributeChange(before=before, after=after)
        before_level = parse_dimension_level(before)
        after_level = parse_dimension_level(after)
        if before_level is None or after_level is None:
            return 0
        return (after_level > before_level) - (after_level < before_level)


class EvolutionSummaryBuilder:
    """Builder for aggregate evolution summaries (Phase 2.1.4)."""

    def build_summary(
        self,
        records: list[RiskEvolutionRecord],
        y1_year: int,
        y2_year: int,
        total_y1_count: int,
        total_y2_count: int,
    ) -> EvolutionSummaryResult:
        """Construct structured summary and verify count invariants."""
        by_status: dict[str, list[RiskEvolutionRecord]] = {
            EvolutionChangeType.NEW.value: [],
            EvolutionChangeType.REMOVED.value: [],
            EvolutionChangeType.UNCHANGED.value: [],
            EvolutionChangeType.MODIFIED.value: [],
            EvolutionChangeType.ESCALATED.value: [],
            EvolutionChangeType.DE_ESCALATED.value: [],
        }

        for r in records:
            status_key = r.change_type.value
            if status_key not in by_status:
                by_status[status_key] = []
            by_status[status_key].append(r)

        new_count = len(by_status[EvolutionChangeType.NEW.value])
        removed_count = len(by_status[EvolutionChangeType.REMOVED.value])
        unchanged_count = len(by_status[EvolutionChangeType.UNCHANGED.value])
        modified_count = len(by_status[EvolutionChangeType.MODIFIED.value])
        escalated_count = len(by_status[EvolutionChangeType.ESCALATED.value])
        de_escalated_count = len(by_status[EvolutionChangeType.DE_ESCALATED.value])

        # Verify summary count invariants
        expected_y1 = unchanged_count + modified_count + escalated_count + de_escalated_count + removed_count
        expected_y2 = unchanged_count + modified_count + escalated_count + de_escalated_count + new_count

        if expected_y1 != total_y1_count:
            logger.warning(
                "y1_summary_count_mismatch", expected=total_y1_count, calculated=expected_y1
            )

        if expected_y2 != total_y2_count:
            logger.warning(
                "y2_summary_count_mismatch", expected=total_y2_count, calculated=expected_y2
            )

        return EvolutionSummaryResult(
            year_1=y1_year,
            year_2=y2_year,
            total_year_1_risks=total_y1_count,
            total_year_2_risks=total_y2_count,
            new_count=new_count,
            removed_count=removed_count,
            unchanged_count=unchanged_count,
            modified_count=modified_count,
            escalated_count=escalated_count,
            de_escalated_count=de_escalated_count,
            records=records,
            by_status=by_status,
        )

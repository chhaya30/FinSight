from collections.abc import Iterable

from app.models.scanner import (
    ContributingFactor,
    ScannerCriterion,
    ScannerEvidence,
    ScannerFactor,
    ScannerResult,
)

SCORE_WEIGHTS = {
    "severity": 0.35,
    "status": 0.25,
    "financial_signal": 0.15,
    "market_signal": 0.15,
    "industry_signal": 0.10,
}
SEVERITY_SCORES = {
    "INFORMATIONAL": 0.15,
    "LOW": 0.30,
    "MEDIUM": 0.55,
    "HIGH": 0.78,
    "CRITICAL": 1.0,
}
STATUS_SCORES = {
    "ESCALATED": 0.90,
    "NEW": 0.70,
    "MODIFIED": 0.65,
    "UNCHANGED": 0.50,
    "REMOVED": 0.50,
    "DE-ESCALATED": 0.35,
    "UNCOMPARED": None,
}


def aggregate_score(factors: Iterable[ContributingFactor]) -> tuple[float, float]:
    """Return normalized observed-signal score and dimension coverage."""
    by_name = {factor.factor: factor for factor in factors}
    observed = [
        (SCORE_WEIGHTS[name], by_name[name].score)
        for name in SCORE_WEIGHTS
        if name in by_name and by_name[name].observed and by_name[name].score is not None
    ]
    if not observed:
        return 0.0, 0.0
    weight_total = sum(weight for weight, _ in observed)
    score = sum(weight * float(value) for weight, value in observed) / weight_total
    return round(score, 4), round(len(observed) / len(SCORE_WEIGHTS), 4)


def matches_criteria(
    factors: Iterable[ContributingFactor], criteria: list[ScannerCriterion], logic: str
) -> bool:
    """Evaluate user criteria against factor values using deterministic comparisons."""
    if not criteria:
        return True
    by_name = {factor.factor: factor for factor in factors}
    checks = []
    for criterion in criteria:
        factor = by_name.get(criterion.factor)
        if criterion.operator == "observed":
            checks.append(factor is not None and factor.observed is criterion.value)
        elif factor is None or not factor.observed:
            checks.append(False)
        elif criterion.operator == "gte":
            try:
                numeric_value = factor.value
                if not isinstance(numeric_value, (float, int)):
                    numeric_value = factor.score
                checks.append(numeric_value is not None and float(numeric_value) >= float(criterion.value))
            except (TypeError, ValueError):
                checks.append(False)
        else:
            checks.append(str(factor.value).casefold() == str(criterion.value).casefold())
    return all(checks) if logic == "AND" else any(checks)


def assessment_for(score: float, coverage: float) -> str:
    if score >= 0.75:
        level = "high"
    elif score >= 0.55:
        level = "elevated"
    elif score >= 0.35:
        level = "moderate"
    else:
        level = "lower"
    count = round(coverage * len(SCORE_WEIGHTS))
    return (
        f"{level.title()} observed risk signals ({score:.2f}) across {count} of "
        f"{len(SCORE_WEIGHTS)} score dimensions. The score summarizes co-occurring "
        "disclosure and provider signals; it does not establish causation or predict an outcome. "
        "Classification confidence and evidence provenance are reported separately and do not inflate the risk score."
    )


def build_result(
    *,
    risk_id: str,
    company_id: str,
    company_name: str,
    sector: str | None,
    report_year: int,
    previous_year: int | None,
    title: str,
    category: str,
    severity: str,
    status: str,
    classification_confidence: float,
    factors: list[ContributingFactor],
) -> ScannerResult:
    evidence_items = [
        evidence
        for factor in factors if factor.factor == "evidence_quality"
        for evidence in factor.evidence
    ]
    evidence_quality = (
        sum(
            sum(bool(value) for value in (
                evidence.document_id, evidence.page, evidence.chunk_id, evidence.excerpt
            )) / 4
            for evidence in evidence_items
        ) / len(evidence_items)
        if evidence_items
        else 0.0
    )
    score, coverage = aggregate_score(factors)
    return ScannerResult(
        risk_id=risk_id,
        company_id=company_id,
        company_name=company_name,
        sector=sector,
        report_year=report_year,
        previous_year=previous_year,
        title=title,
        category=category,
        severity=severity,
        status=status,
        classification_confidence=round(max(0.0, min(1.0, classification_confidence)), 4),
        evidence_quality=round(evidence_quality, 4),
        overall_score=score,
        assessment=assessment_for(score, coverage),
        coverage=coverage,
        matched=False,
        contributing_factors=factors,
    )


def attach_match(result: ScannerResult, matched: bool) -> ScannerResult:
    return result.model_copy(update={"matched": matched})

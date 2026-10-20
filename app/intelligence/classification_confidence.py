"""Deterministic, evidence-aware confidence assessment for stored risk labels."""

from dataclasses import dataclass
import math

from app.taxonomy.classifier_rules import RuleBasedClassifier, SeverityRules


@dataclass(frozen=True)
class ClassificationConfidence:
    category: float
    severity: float
    classification: float
    evidence_quality: float
    low_confidence: bool
    reason: str


def assess_classification_confidence(
    *, category: str | None, severity: str | None, stored_confidence: float | None,
    evidence_text: str | None, source_document: str | None, page: int | None,
    chunk_available: bool = False,
) -> ClassificationConfidence:
    """Assess stored labels from existing Phase 2 rules and available provenance.

    Scores are deterministic support indicators, not calibrated probabilities.
    Missing inputs score zero and never receive a favorable default.
    """
    text = (evidence_text or "").strip()
    if not text:
        return ClassificationConfidence(
            category=0.0, severity=0.0, classification=0.0, evidence_quality=0.0,
            low_confidence=True,
            reason="No source text is available; category, severity, and classification confidence cannot be supported.",
        )

    words = len(text.split())
    provenance = int(bool(source_document)) + int(page is not None) + int(chunk_available)
    evidence_quality = min(1.0, words / 40.0) * (0.6 + (0.4 / 3.0) * provenance)
    evidence_quality = round(evidence_quality, 4)

    category_scores = RuleBasedClassifier().classify(text)
    matching_category_score = next(
        (score for label, score in category_scores.items() if category and label.casefold() == category.casefold()),
        0.0,
    )
    category_support = (
        min(1.0, matching_category_score / 2.0) if matching_category_score
        else 0.25 if category else 0.0
    )

    inferred_severity = SeverityRules.classify_severity(text, category)
    severity_support = (
        1.0 if severity and inferred_severity.casefold() == severity.casefold()
        else 0.25 if severity else 0.0
    )

    category_confidence = round(category_support * evidence_quality, 4)
    severity_confidence = round(severity_support * evidence_quality, 4)
    stored = float(stored_confidence) if stored_confidence is not None and math.isfinite(stored_confidence) else 0.0
    stored = max(0.0, min(1.0, stored))
    classification = round(stored * evidence_quality, 4)
    low = min(category_confidence, severity_confidence, classification) < 0.6
    reason = (
        f"Existing Phase 2 category rules provide {'matching' if matching_category_score else 'no matching'} support; "
        f"existing severity rules {'agree' if severity_support == 1.0 else 'do not agree'} with the stored severity. "
        f"Evidence quality is {evidence_quality:.0%} from {words} words and {provenance}/3 available document/page/chunk fields. "
        f"Stored classification confidence {stored:.0%} is adjusted by evidence quality; these scores are support indicators, not probabilities."
    )
    return ClassificationConfidence(
        category=category_confidence, severity=severity_confidence,
        classification=classification, evidence_quality=evidence_quality,
        low_confidence=low, reason=reason,
    )

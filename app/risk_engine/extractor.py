from dataclasses import dataclass
from typing import Any

from app.config.logging import get_logger
from app.risk_engine.detector import RiskCandidate
from app.taxonomy.classifier_rules import RuleBasedClassifier, SeverityRules
from app.taxonomy.loader import get_taxonomy

logger = get_logger(__name__)


@dataclass
class ExtractedRisk:
    candidate: RiskCandidate
    category: str
    subcategory: str | None = None
    severity: str = "medium"
    confidence_score: float = 0.0
    summary: str = ""
    entities: list[dict[str, Any]] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.entities is None:
            self.entities = []
        if self.metadata is None:
            self.metadata = {}


class RiskExtractor:
    def __init__(self):
        self.taxonomy = get_taxonomy()
        self.classifier = RuleBasedClassifier()

    def extract(self, candidates: list[RiskCandidate]) -> list[ExtractedRisk]:
        extracted = []

        for candidate in candidates:
            category = self._classify_category(candidate.text)
            severity = self._classify_severity(candidate.text, category)
            confidence = self._calculate_confidence(candidate, category, severity)
            summary = self._generate_summary(candidate.text)
            entities = self._extract_entities(candidate.text)

            risk = ExtractedRisk(
                candidate=candidate,
                category=category,
                severity=severity,
                confidence_score=confidence,
                summary=summary,
                entities=entities,
                metadata={
                    "source_section": candidate.source_section,
                    "source_page": candidate.source_page,
                    "paragraph_index": candidate.paragraph_index,
                },
            )
            extracted.append(risk)

        logger.info("risks_extracted", count=len(extracted))
        return extracted

    def _classify_category(self, text: str) -> str:
        scores = self.classifier.classify(text)
        if scores:
            return max(scores, key=scores.get)

        matches = self.taxonomy.match_category(text, threshold=1)
        if matches:
            return matches[0]

        return "general"

    def _classify_severity(self, text: str, category: str) -> str:
        return SeverityRules.classify_severity(text, category)

    def _calculate_confidence(
        self, candidate: RiskCandidate, category: str, severity: str
    ) -> float:
        base_confidence = candidate.confidence

        category_boost = 0.0
        if category != "general":
            category_boost = 0.15

        severity_boost = 0.0
        severity_weights = {
            "critical": 0.15,
            "high": 0.1,
            "medium": 0.05,
            "low": 0.0,
            "informational": -0.05,
        }
        severity_boost = severity_weights.get(severity, 0.0)

        length_factor = min(len(candidate.text) / 1000.0, 0.1)

        confidence = base_confidence + category_boost + severity_boost + length_factor
        return min(max(confidence, 0.0), 1.0)

    def _generate_summary(self, text: str) -> str:
        sentences = text.split(". ")
        if len(sentences) <= 2:
            return text[:500]
        return ". ".join(sentences[:2]) + "."

    def _extract_entities(self, text: str) -> list[dict[str, Any]]:
        entities = []

        import re

        money_matches = re.findall(r"\b(?:₹|\$|Rs\.?|USD|INR)\s*[\d,]+(?:\.\d+)?\b", text)
        for match in money_matches[:5]:
            entities.append({"type": "MONEY", "text": match})

        percent_matches = re.findall(r"\b\d+(?:\.\d+)?%\b", text)
        for match in percent_matches[:5]:
            entities.append({"type": "PERCENT", "text": match})

        date_matches = re.findall(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", text)
        for match in date_matches[:5]:
            entities.append({"type": "DATE", "text": match})

        return entities


class LLMBasedRiskExtractor(RiskExtractor):
    def __init__(self, llm_client=None):
        super().__init__()
        self.llm_client = llm_client

    def extract(self, candidates: list[RiskCandidate]) -> list[ExtractedRisk]:
        if self.llm_client:
            return self._extract_with_llm(candidates)
        return super().extract(candidates)

    def _extract_with_llm(self, candidates: list[RiskCandidate]) -> list[ExtractedRisk]:
        return super().extract(candidates)


def extract_risks(candidates: list[RiskCandidate]) -> list[ExtractedRisk]:
    extractor = RiskExtractor()
    return extractor.extract(candidates)

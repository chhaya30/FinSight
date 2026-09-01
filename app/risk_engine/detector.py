from dataclasses import dataclass

from app.config.logging import get_logger
from app.processing import (
    DocumentSection,
    extract_risk_paragraphs,
    find_risk_factors_section,
    split_into_risk_statements,
)

logger = get_logger(__name__)


@dataclass
class RiskCandidate:
    text: str
    source_section: str
    source_page: int
    paragraph_index: int
    confidence: float = 0.0
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class RiskDetector:
    def __init__(self, min_confidence: float = 0.3):
        self.min_confidence = min_confidence
        self.risk_indicators = [
            "risk",
            "uncertainty",
            "adverse",
            "material",
            "significant",
            "potential",
            "exposure",
            "vulnerability",
            "threat",
            "challenge",
            "impact",
            "consequence",
            "likelihood",
            "probability",
            "may",
            "could",
            "might",
            "can",
            "will",
            "would",
            "potentially",
            "possibly",
            "likely",
            "unlikely",
        ]

    def detect(self, sections: list[DocumentSection]) -> list[RiskCandidate]:
        risk_section = find_risk_factors_section(sections)

        if not risk_section:
            logger.warning("no_risk_section_found")
            return []

        paragraphs = extract_risk_paragraphs(risk_section)
        statements = split_into_risk_statements(paragraphs)

        candidates = []
        for idx, statement in enumerate(statements):
            confidence = self._calculate_confidence(statement)
            if confidence >= self.min_confidence:
                candidates.append(
                    RiskCandidate(
                        text=statement,
                        source_section=risk_section.title,
                        source_page=risk_section.start_page,
                        paragraph_index=idx,
                        confidence=confidence,
                    )
                )

        logger.info("risk_candidates_detected", count=len(candidates))
        return candidates

    def _calculate_confidence(self, text: str) -> float:
        text_lower = text.lower()

        indicator_count = sum(1 for ind in self.risk_indicators if ind in text_lower)
        indicator_score = min(indicator_count / 5.0, 1.0)

        length_score = min(len(text) / 500.0, 1.0)

        structure_score = 0.0
        if any(kw in text_lower for kw in ["may", "could", "might", "potentially"]):
            structure_score += 0.3
        if any(kw in text_lower for kw in ["risk", "uncertainty", "exposure", "adverse"]):
            structure_score += 0.3
        if any(kw in text_lower for kw in ["impact", "effect", "consequence", "result"]):
            structure_score += 0.2
        if "." in text and len(text.split(".")) >= 2:
            structure_score += 0.2

        confidence = indicator_score * 0.4 + length_score * 0.2 + structure_score * 0.4
        return min(confidence, 1.0)


class AdvancedRiskDetector(RiskDetector):
    def __init__(self, min_confidence: float = 0.3, use_llm: bool = False):
        super().__init__(min_confidence)
        self.use_llm = use_llm

    def detect(self, sections: list[DocumentSection]) -> list[RiskCandidate]:
        candidates = super().detect(sections)

        if self.use_llm:
            candidates = self._enhance_with_llm(candidates)

        return candidates

    def _enhance_with_llm(self, candidates: list[RiskCandidate]) -> list[RiskCandidate]:
        return candidates


def detect_risks(
    sections: list[DocumentSection], min_confidence: float = 0.3
) -> list[RiskCandidate]:
    detector = RiskDetector(min_confidence=min_confidence)
    return detector.detect(sections)

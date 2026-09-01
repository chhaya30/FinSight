from app.config.logging import get_logger
from app.processing.section_detector import (
    DocumentSection,
)
from app.processing.section_detector import (
    RiskSectionDetector as BaseRiskSectionDetector,
)

logger = get_logger(__name__)


class RiskSectionDetector:
    def __init__(self):
        self.detector = BaseRiskSectionDetector()

    def find_risk_factors_section(self, sections: list[DocumentSection]) -> DocumentSection | None:
        for section in sections:
            if self._is_risk_factors(section):
                return section
            if section.subsections:
                found = self.find_risk_factors_section(section.subsections)
                if found:
                    return found
        return None

    def _is_risk_factors(self, section: DocumentSection) -> bool:
        title_lower = section.title.lower()
        risk_factor_keywords = [
            "risk factors",
            "principal risks",
            "key risks",
            "material risks",
            "enterprise risks",
            "significant risks",
        ]
        return any(kw in title_lower for kw in risk_factor_keywords)

    def extract_risk_paragraphs(self, section: DocumentSection) -> list[str]:
        paragraphs = section.content.split("\n\n")
        risk_paragraphs = []

        for para in paragraphs:
            para = para.strip()
            if len(para) < 50:
                continue
            if self._contains_risk_language(para):
                risk_paragraphs.append(para)

        return risk_paragraphs

    def _contains_risk_language(self, text: str) -> bool:
        text_lower = text.lower()
        risk_verbs = [
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
        risk_nouns = [
            "risk",
            "uncertainty",
            "exposure",
            "vulnerability",
            "threat",
            "adverse impact",
            "negative impact",
            "material effect",
            "significant effect",
        ]

        has_risk_verb = any(verb in text_lower for verb in risk_verbs)
        has_risk_noun = any(noun in text_lower for noun in risk_nouns)

        return has_risk_verb or has_risk_noun

    def split_into_risk_statements(self, paragraphs: list[str]) -> list[str]:
        statements = []

        for para in paragraphs:
            sentences = self._split_sentences(para)
            current_statement = ""

            for sentence in sentences:
                current_statement += " " + sentence

                if self._is_complete_risk_statement(current_statement):
                    statements.append(current_statement.strip())
                    current_statement = ""

            if current_statement.strip() and len(current_statement.strip()) > 50:
                statements.append(current_statement.strip())

        return statements

    def _split_sentences(self, text: str) -> list[str]:
        import re

        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
        return [s.strip() for s in sentences if s.strip()]

    def _is_complete_risk_statement(self, text: str) -> bool:
        text_lower = text.lower()
        has_risk_content = any(
            kw in text_lower
            for kw in [
                "risk",
                "uncertainty",
                "exposure",
                "adverse",
                "material",
                "significant",
                "impact",
                "effect",
            ]
        )
        has_complete_structure = text.count(".") >= 1 and len(text) > 100
        return has_risk_content and has_complete_structure


def find_risk_factors_section(sections: list[DocumentSection]) -> DocumentSection | None:
    detector = RiskSectionDetector()
    return detector.find_risk_factors_section(sections)


def extract_risk_paragraphs(section: DocumentSection) -> list[str]:
    detector = RiskSectionDetector()
    return detector.extract_risk_paragraphs(section)


def split_into_risk_statements(paragraphs: list[str]) -> list[str]:
    detector = RiskSectionDetector()
    return detector.split_into_risk_statements(paragraphs)

import hashlib
from dataclasses import dataclass
from typing import Any

from app.config.logging import get_logger
from app.models.document import PageContent
from app.risk_engine.extractor import ExtractedRisk

logger = get_logger(__name__)


@dataclass
class Evidence:
    risk_id: str
    source_text: str
    source_page: int
    source_paragraph: str
    text_hash: str
    char_start: int
    char_end: int
    context_before: str = ""
    context_after: str = ""
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class EvidenceBuilder:
    def __init__(self, context_window: int = 200):
        self.context_window = context_window

    def build_evidence(
        self, risks: list[ExtractedRisk], pages: list[PageContent]
    ) -> list[Evidence]:
        evidence_list = []

        for risk in risks:
            evidence = self._create_evidence(risk, pages)
            if evidence:
                evidence_list.append(evidence)

        logger.info("evidence_built", count=len(evidence_list))
        return evidence_list

    def _create_evidence(self, risk: ExtractedRisk, pages: list[PageContent]) -> Evidence | None:
        source_page = risk.candidate.source_page
        source_text = risk.candidate.text

        if source_page < 1 or source_page > len(pages):
            logger.warning(
                "invalid_source_page",
                risk_id=risk.candidate.text[:50],
                page=source_page,
            )
            return None

        page_content = pages[source_page - 1]
        full_text = page_content.text

        char_start = full_text.find(source_text[:100])
        if char_start == -1:
            char_start = 0
        char_end = char_start + len(source_text)

        context_before = full_text[max(0, char_start - self.context_window) : char_start]
        context_after = full_text[char_end : char_end + self.context_window]

        text_hash = hashlib.sha256(source_text.encode()).hexdigest()[:16]

        return Evidence(
            risk_id=risk.candidate.text[:50],
            source_text=source_text,
            source_page=source_page,
            source_paragraph=source_text[:500],
            text_hash=text_hash,
            char_start=char_start,
            char_end=char_end,
            context_before=context_before.strip(),
            context_after=context_after.strip(),
            metadata={
                "section": risk.candidate.source_section,
                "paragraph_index": risk.candidate.paragraph_index,
                "category": risk.category,
                "severity": risk.severity,
            },
        )

    def build_comparison_evidence(
        self,
        risk_prev: ExtractedRisk,
        risk_current: ExtractedRisk,
        pages_prev: list[PageContent],
        pages_current: list[PageContent],
    ) -> dict[str, Evidence]:
        evidence_prev = self._create_evidence(risk_prev, pages_prev)
        evidence_current = self._create_evidence(risk_current, pages_current)

        return {
            "previous": evidence_prev,
            "current": evidence_current,
        }


def build_evidence(risks: list[ExtractedRisk], pages: list[PageContent]) -> list[Evidence]:
    builder = EvidenceBuilder()
    return builder.build_evidence(risks, pages)

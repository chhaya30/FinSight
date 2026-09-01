from dataclasses import dataclass

from app.config.logging import get_logger
from app.risk_engine.extractor import ExtractedRisk

logger = get_logger(__name__)


@dataclass
class DuplicateGroup:
    risks: list[ExtractedRisk]
    representative: ExtractedRisk
    similarity_scores: dict[int, float]


class RiskDeduplicator:
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold

    def deduplicate(self, risks: list[ExtractedRisk]) -> list[ExtractedRisk]:
        if len(risks) <= 1:
            return risks

        groups = self._find_duplicate_groups(risks)
        deduplicated = []

        for group in groups:
            deduplicated.append(group.representative)

        logger.info(
            "risks_deduplicated",
            original=len(risks),
            deduplicated=len(deduplicated),
            removed=len(risks) - len(deduplicated),
        )
        return deduplicated

    def _find_duplicate_groups(self, risks: list[ExtractedRisk]) -> list[DuplicateGroup]:
        groups = []
        used = set()

        for i, risk in enumerate(risks):
            if i in used:
                continue

            group_risks = [risk]
            scores = {i: 1.0}

            for j, other in enumerate(risks[i + 1 :], start=i + 1):
                if j in used:
                    continue

                similarity = self._calculate_similarity(risk, other)
                if similarity >= self.similarity_threshold:
                    group_risks.append(other)
                    scores[j] = similarity
                    used.add(j)

            representative = self._select_representative(group_risks)
            groups.append(
                DuplicateGroup(
                    risks=group_risks,
                    representative=representative,
                    similarity_scores=scores,
                )
            )

            used.add(i)

        return groups

    def _calculate_similarity(self, risk1: ExtractedRisk, risk2: ExtractedRisk) -> float:
        text1 = risk1.candidate.text.lower()
        text2 = risk2.candidate.text.lower()

        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        jaccard = len(intersection) / len(union)

        category_match = 1.0 if risk1.category == risk2.category else 0.0
        severity_match = 1.0 if risk1.severity == risk2.severity else 0.0

        combined = (jaccard * 0.7) + (category_match * 0.15) + (severity_match * 0.15)
        return combined

    def _select_representative(self, risks: list[ExtractedRisk]) -> ExtractedRisk:
        return max(risks, key=lambda r: r.confidence_score)


class SemanticDeduplicator(RiskDeduplicator):
    def __init__(self, similarity_threshold: float = 0.85, embedding_model=None):
        super().__init__(similarity_threshold)
        self.embedding_model = embedding_model

    def _calculate_similarity(self, risk1: ExtractedRisk, risk2: ExtractedRisk) -> float:
        if self.embedding_model:
            return self._semantic_similarity(risk1, risk2)
        return super()._calculate_similarity(risk1, risk2)

    def _semantic_similarity(self, risk1: ExtractedRisk, risk2: ExtractedRisk) -> float:
        return super()._calculate_similarity(risk1, risk2)


def deduplicate_risks(risks: list[ExtractedRisk], threshold: float = 0.85) -> list[ExtractedRisk]:
    deduplicator = RiskDeduplicator(similarity_threshold=threshold)
    return deduplicator.deduplicate(risks)

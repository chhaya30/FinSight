import difflib
from typing import Any

from app.comparison.normalizer import RiskNormalizer
from app.config.constants import (
    MATCH_CONFIDENCE_THRESHOLD,
    SIMILARITY_THRESHOLD_MATCH,
    SIMILARITY_THRESHOLD_NEW_RISK,
)
from app.config.logging import get_logger
from app.models.comparison import CandidateMatch, RiskMatchResult
from app.models.risk import NormalizedRisk
from app.retrieval.embeddings import cosine_similarity


logger = get_logger(__name__)


def calculate_text_similarity(str1: str, str2: str) -> float:
    """Calculate SequenceMatcher similarity between two strings."""
    if not str1 or not str2:
        return 0.0
    s1 = str1.strip().lower()
    s2 = str2.strip().lower()
    if s1 == s2:
        return 1.0
    return difflib.SequenceMatcher(None, s1, s2).ratio()


def calculate_jaccard_overlap(str1: str, str2: str) -> float:
    """Calculate word token Jaccard similarity between two strings."""
    if not str1 or not str2:
        return 0.0
    set1 = set(str1.lower().split())
    set2 = set(str2.lower().split())
    if not set1 or not set2:
        return 0.0
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    return len(intersection) / len(union)


class SemanticRiskMatcher:
    """Service to compute semantic similarity and candidate matches between Year 2 and Year 1 risks."""

    def __init__(
        self,
        embedding_provider: Any | None = None,
        min_similarity_threshold: float = SIMILARITY_THRESHOLD_NEW_RISK,
        min_confidence_threshold: float = MATCH_CONFIDENCE_THRESHOLD,
        weight_semantic: float = 0.65,
        weight_category: float = 0.20,
        weight_title: float = 0.15,
    ):
        self.embedding_provider = embedding_provider
        self.min_similarity_threshold = min_similarity_threshold
        self.min_confidence_threshold = min_confidence_threshold
        self.weight_semantic = weight_semantic
        self.weight_category = weight_category
        self.weight_title = weight_title

    async def _ensure_embeddings(self, risks: list[NormalizedRisk]) -> None:
        """Ensure all risks in the list have vector embeddings if provider is available."""
        missing_indices = [i for i, r in enumerate(risks) if not r.embedding]
        if not missing_indices or self.embedding_provider is None:
            return

        texts = [f"{risks[i].title}. {risks[i].description}".strip() for i in missing_indices]
        try:
            embeddings = await self.embedding_provider.embed(texts)
            for i, emb in zip(missing_indices, embeddings, strict=False):
                risks[i].embedding = emb

        except Exception as e:
            logger.warning("embedding_generation_failed", error=str(e))

    async def match_risk(
        self,
        y2_risk: NormalizedRisk | dict[str, Any],
        y1_candidates: list[NormalizedRisk | dict[str, Any]],
        y2_year: int = 2025,
        y1_year: int = 2024,
    ) -> RiskMatchResult:
        """Find candidate Year-1 matches for a single Year-2 risk."""
        normalizer = RiskNormalizer(self.embedding_provider)

        norm_y2 = (
            y2_risk
            if isinstance(y2_risk, NormalizedRisk)
            else normalizer.normalize(y2_risk, report_year=y2_year)
        )
        norm_y1_list = [
            r if isinstance(r, NormalizedRisk) else normalizer.normalize(r, report_year=y1_year)
            for r in y1_candidates
        ]

        # Ensure embeddings for all risks
        await self._ensure_embeddings([norm_y2] + norm_y1_list)

        candidate_matches: list[CandidateMatch] = []

        for norm_y1 in norm_y1_list:
            # 1. Semantic vector similarity
            sem_sim = 0.0
            if norm_y2.embedding and norm_y1.embedding:
                try:
                    sem_sim = max(0.0, cosine_similarity(norm_y2.embedding, norm_y1.embedding))
                except Exception:
                    sem_sim = 0.0

            # Text similarity fallback if no embeddings present or as secondary check
            text_sim = calculate_text_similarity(norm_y2.description, norm_y1.description)
            if not norm_y2.embedding or not norm_y1.embedding:
                sem_sim = text_sim

            # 2. Title similarity
            title_sim = max(
                calculate_text_similarity(norm_y2.title, norm_y1.title),
                calculate_jaccard_overlap(norm_y2.title, norm_y1.title),
            )

            # 3. Category match signal
            cat2 = (norm_y2.category or "").strip().lower()
            cat1 = (norm_y1.category or "").strip().lower()
            category_match = bool(cat2 and cat1 and (cat2 == cat1 or cat2 in cat1 or cat1 in cat2))
            cat_score = 1.0 if category_match else 0.0

            # Composite Match Confidence Score
            confidence = (
                self.weight_semantic * sem_sim
                + self.weight_category * cat_score
                + self.weight_title * title_sim
            )
            confidence = min(max(confidence, 0.0), 1.0)

            if (
                sem_sim >= self.min_similarity_threshold
                or confidence >= self.min_confidence_threshold
            ):
                if sem_sim < SIMILARITY_THRESHOLD_NEW_RISK:
                    similarity_band = "weak"
                elif sem_sim < SIMILARITY_THRESHOLD_MATCH:
                    similarity_band = "review"
                else:
                    similarity_band = "strong"
                candidate_matches.append(
                    CandidateMatch(
                        year_1_risk_id=norm_y1.risk_id,
                        semantic_similarity=round(sem_sim, 4),
                        match_confidence=round(confidence, 4),
                        category_match=category_match,
                        title_similarity=round(title_sim, 4),
                        matching_signals={
                            "semantic_similarity": round(sem_sim, 4),
                            "title_similarity": round(title_sim, 4),
                            "category_match": category_match,
                            "text_similarity": round(text_sim, 4),
                            "similarity_band": similarity_band,
                        },
                    )
                )

        # Sort candidate matches by confidence in descending order
        candidate_matches.sort(key=lambda m: m.match_confidence, reverse=True)

        best_match = (
            candidate_matches[0]
            if candidate_matches
            and candidate_matches[0].match_confidence >= self.min_confidence_threshold
            else None
        )

        return RiskMatchResult(
            year_2_risk_id=norm_y2.risk_id,
            candidate_matches=candidate_matches,
            best_match=best_match,
        )

    async def match_all_risks(
        self,
        y2_risks: list[NormalizedRisk | dict[str, Any]],
        y1_risks: list[NormalizedRisk | dict[str, Any]],
        y2_year: int = 2025,
        y1_year: int = 2024,
    ) -> list[RiskMatchResult]:
        """Match all Year-2 risks against candidate Year-1 risks."""
        results = []
        for y2 in y2_risks:
            res = await self.match_risk(y2, y1_risks, y2_year=y2_year, y1_year=y1_year)
            results.append(res)
        return results

from collections.abc import Callable
from typing import Any, Optional

from app.config.logging import get_logger

logger = get_logger(__name__)


def reciprocal_rank_fusion(
    result_lists: list[list[dict[str, Any]]],
    k: int = 60,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    score_map = {}

    for results in result_lists:
        for rank, result in enumerate(results):
            doc_id = result["id"]
            if doc_id not in score_map:
                score_map[doc_id] = {
                    "id": doc_id,
                    "text": result["text"],
                    "rrf_score": 0.0,
                    "metadata": result.get("metadata", {}),
                }
            score_map[doc_id]["rrf_score"] += 1.0 / (k + rank + 1)

    fused = list(score_map.values())
    fused.sort(key=lambda x: x["rrf_score"], reverse=True)
    return fused[:top_k]


def weighted_reciprocal_rank_fusion(
    result_lists: list[list[dict[str, Any]]],
    weights: list[float],
    k: int = 60,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    if len(result_lists) != len(weights):
        raise ValueError("Number of result lists must match number of weights")

    score_map = {}

    for weight, results in zip(weights, result_lists, strict=True):
        for rank, result in enumerate(results):
            doc_id = result["id"]
            if doc_id not in score_map:
                score_map[doc_id] = {
                    "id": doc_id,
                    "text": result["text"],
                    "rrf_score": 0.0,
                    "metadata": result.get("metadata", {}),
                }
            score_map[doc_id]["rrf_score"] += weight / (k + rank + 1)

    fused = list(score_map.values())
    fused.sort(key=lambda x: x["rrf_score"], reverse=True)
    return fused[:top_k]


class RRFRetriever:
    def __init__(
        self,
        retrievers: list[Callable],
        weights: Optional[list[float]] = None,
        k: int = 60,
    ):
        self.retrievers = retrievers
        self.weights = weights or [1.0] * len(retrievers)
        self.k = k

    async def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        result_lists = []

        for retriever in self.retrievers:
            try:
                if hasattr(retriever, "search"):
                    results = await retriever.search(query, top_k=top_k * 2)
                else:
                    results = retriever(query, top_k=top_k * 2)
                result_lists.append(results)
            except Exception as e:
                logger.warning("retriever_failed", error=str(e))
                result_lists.append([])

        if self.weights:
            return weighted_reciprocal_rank_fusion(result_lists, self.weights, self.k, top_k)
        return reciprocal_rank_fusion(result_lists, self.k, top_k)


def create_rrf_retriever(
    retrievers: list, weights: list[float] = None, k: int = 60
) -> RRFRetriever:
    return RRFRetriever(retrievers, weights, k)

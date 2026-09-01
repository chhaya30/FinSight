from abc import ABC, abstractmethod
from typing import Any

from app.config.logging import get_logger

logger = get_logger(__name__)


class BaseReranker(ABC):
    @abstractmethod
    async def rerank(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        pass


class CrossEncoderReranker(BaseReranker):
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder

                self._model = CrossEncoder(self.model_name)
                logger.info("reranker_model_loaded", model=self.model_name)
            except ImportError:
                logger.error("sentence_transformers_not_installed")
                raise

    async def rerank(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        if not results:
            return []

        self._load_model()

        pairs = [(query, result["text"]) for result in results]
        scores = self._model.predict(pairs)

        reranked = []
        for result, score in zip(results, scores, strict=True):
            reranked.append(
                {
                    **result,
                    "rerank_score": float(score),
                }
            )

        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
        return reranked[:top_k]


class LLMReranker(BaseReranker):
    def __init__(self, llm_provider=None):
        self.llm_provider = llm_provider

    async def rerank(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        if not results or not self.llm_provider:
            return results[:top_k]

        candidates_text = "\n\n".join(
            [f"[{i}] {result['text'][:500]}" for i, result in enumerate(results[:20])]
        )

        prompt = f"""Given the query: "{query}"

Rank the following candidate passages by relevance (most relevant first):

{candidates_text}

Return a JSON array of indices in ranked order, e.g., [2, 0, 5, 1, ...]"""

        try:
            from app.llm.base import create_user_message

            messages = [create_user_message(prompt)]
            response = await self.llm_provider.generate(messages)

            import json

            ranked_indices = json.loads(response.content.strip())

            reranked = []
            for idx in ranked_indices:
                if 0 <= idx < len(results):
                    reranked.append(
                        {
                            **results[idx],
                            "llm_rerank_score": len(ranked_indices) - ranked_indices.index(idx),
                        }
                    )
                    if len(reranked) >= top_k:
                        break

            return reranked
        except Exception as e:
            logger.warning("llm_rerank_failed", error=str(e))
            return results[:top_k]


class HeuristicReranker(BaseReranker):
    def __init__(self):
        pass

    async def rerank(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        if not results:
            return []

        query_terms = set(query.lower().split())

        for result in results:
            text_terms = set(result["text"].lower().split())
            overlap = len(query_terms & text_terms)
            result["heuristic_score"] = overlap / max(len(query_terms), 1)

        results.sort(key=lambda x: x.get("heuristic_score", 0), reverse=True)
        return results[:top_k]


def create_reranker(reranker_type: str = "heuristic", **kwargs) -> BaseReranker:
    if reranker_type == "cross-encoder":
        return CrossEncoderReranker(**kwargs)
    elif reranker_type == "llm":
        return LLMReranker(**kwargs)
    else:
        return HeuristicReranker()

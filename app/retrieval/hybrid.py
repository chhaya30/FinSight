from dataclasses import dataclass
from typing import Any

from app.config.logging import get_logger
from app.retrieval.bm25 import BM25Document, BM25Retriever
from app.retrieval.dense_retriever import DenseDocument, DenseRetriever

logger = get_logger(__name__)


@dataclass
class HybridDocument:
    id: str
    text: str
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class HybridRetriever:
    def __init__(
        self,
        bm25_retriever: BM25Retriever | None = None,
        dense_retriever: DenseRetriever | None = None,
        bm25_weight: float = 0.5,
        dense_weight: float = 0.5,
    ):
        self.bm25 = bm25_retriever or BM25Retriever()
        self.dense = dense_retriever or DenseRetriever()
        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight

    def add_documents(self, documents: list[HybridDocument]) -> None:
        bm25_docs = [BM25Document(id=d.id, text=d.text, metadata=d.metadata) for d in documents]
        dense_docs = [DenseDocument(id=d.id, text=d.text, metadata=d.metadata) for d in documents]

        self.bm25.add_documents(bm25_docs)
        self.dense.add_documents(dense_docs)

    async def search(
        self,
        query: str,
        top_k: int = 10,
        bm25_top_k: int = 50,
        dense_top_k: int = 50,
    ) -> list[dict[str, Any]]:
        bm25_results = self.bm25.search(query, top_k=bm25_top_k)
        dense_results = await self.dense.search(query, top_k=dense_top_k)

        combined = self._merge_results(bm25_results, dense_results)
        return combined[:top_k]

    def _merge_results(
        self,
        bm25_results: list[dict[str, Any]],
        dense_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        score_map = {}

        for result in bm25_results:
            doc_id = result["id"]
            if doc_id not in score_map:
                score_map[doc_id] = {
                    "id": doc_id,
                    "text": result["text"],
                    "bm25_score": 0.0,
                    "dense_score": 0.0,
                    "metadata": result.get("metadata", {}),
                }
            score_map[doc_id]["bm25_score"] = result["score"]

        for result in dense_results:
            doc_id = result["id"]
            if doc_id not in score_map:
                score_map[doc_id] = {
                    "id": doc_id,
                    "text": result["text"],
                    "bm25_score": 0.0,
                    "dense_score": 0.0,
                    "metadata": result.get("metadata", {}),
                }
            score_map[doc_id]["dense_score"] = result["score"]

        max_bm25 = max((r["bm25_score"] for r in score_map.values()), default=1.0)
        max_dense = max((r["dense_score"] for r in score_map.values()), default=1.0)

        combined = []
        for doc in score_map.values():
            norm_bm25 = doc["bm25_score"] / max_bm25 if max_bm25 > 0 else 0
            norm_dense = doc["dense_score"] / max_dense if max_dense > 0 else 0

            combined_score = norm_bm25 * self.bm25_weight + norm_dense * self.dense_weight

            combined.append(
                {
                    "id": doc["id"],
                    "text": doc["text"],
                    "score": combined_score,
                    "bm25_score": doc["bm25_score"],
                    "dense_score": doc["dense_score"],
                    "metadata": doc["metadata"],
                }
            )

        combined.sort(key=lambda x: x["score"], reverse=True)
        return combined

    def clear(self) -> None:
        self.bm25.clear()
        self.dense.clear()


def create_hybrid_retriever(**kwargs) -> HybridRetriever:
    return HybridRetriever(**kwargs)

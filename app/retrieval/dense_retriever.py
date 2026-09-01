from dataclasses import dataclass
from typing import Any

import numpy as np

from app.config.logging import get_logger
from app.retrieval.embeddings import (
    EmbeddingProvider,
    batch_cosine_similarity,
    create_embedding_provider,
)

logger = get_logger(__name__)


@dataclass
class DenseDocument:
    id: str
    text: str
    embedding: list[float] | None = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DenseRetriever:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider | None = None,
        provider_name: str | None = None,
    ):
        self.embedding_provider = embedding_provider or create_embedding_provider(provider_name)
        self.documents: list[DenseDocument] = []
        self.embeddings_matrix: np.ndarray | None = None

    async def add_documents(self, documents: list[DenseDocument]) -> None:
        new_docs = [d for d in documents if d.embedding is None]
        if new_docs:
            texts = [d.text for d in new_docs]
            embeddings = await self.embedding_provider.embed(texts)
            for doc, emb in zip(new_docs, embeddings, strict=True):
                doc.embedding = emb

        self.documents.extend(documents)
        self._rebuild_matrix()

    def _rebuild_matrix(self) -> None:
        if self.documents:
            self.embeddings_matrix = np.array([d.embedding for d in self.documents])
        else:
            self.embeddings_matrix = None

    async def search(
        self, query: str, top_k: int = 10, threshold: float = 0.0
    ) -> list[dict[str, Any]]:
        if not self.documents or self.embeddings_matrix is None:
            return []

        query_embedding = await self.embedding_provider.embed_query(query)
        similarities = batch_cosine_similarity(query_embedding, self.embeddings_matrix.tolist())

        results = []
        for idx, score in enumerate(similarities):
            if score >= threshold:
                doc = self.documents[idx]
                results.append(
                    {
                        "id": doc.id,
                        "text": doc.text,
                        "score": float(score),
                        "metadata": doc.metadata,
                    }
                )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    async def search_by_embedding(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        if not self.documents or self.embeddings_matrix is None:
            return []

        similarities = batch_cosine_similarity(query_embedding, self.embeddings_matrix.tolist())

        results = []
        for idx, score in enumerate(similarities):
            if score >= threshold:
                doc = self.documents[idx]
                results.append(
                    {
                        "id": doc.id,
                        "text": doc.text,
                        "score": float(score),
                        "metadata": doc.metadata,
                    }
                )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def clear(self) -> None:
        self.documents = []
        self.embeddings_matrix = None


def create_dense_retriever(**kwargs) -> DenseRetriever:
    return DenseRetriever(**kwargs)

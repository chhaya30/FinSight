import math
from collections import Counter
from dataclasses import dataclass
from typing import Any

from app.config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BM25Document:
    id: str
    text: str
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BM25Retriever:
    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        epsilon: float = 0.25,
    ):
        self.k1 = k1
        self.b = b
        self.epsilon = epsilon

        self.documents: list[BM25Document] = []
        self.doc_freqs: dict[str, int] = {}
        self.doc_lens: list[int] = []
        self.avgdl: float = 0
        self._tokenized_docs: list[list[str]] = []

    def add_documents(self, documents: list[BM25Document]) -> None:
        self.documents.extend(documents)
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        self.doc_freqs = {}
        self.doc_lens = []
        self._tokenized_docs = []

        for doc in self.documents:
            tokens = self._tokenize(doc.text)
            self._tokenized_docs.append(tokens)
            self.doc_lens.append(len(tokens))

            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

        if self.doc_lens:
            self.avgdl = sum(self.doc_lens) / len(self.doc_lens)

    def _tokenize(self, text: str) -> list[str]:
        import re

        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        return [t for t in text.split() if len(t) > 2]

    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        if not self.documents:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores = []
        for i, doc_tokens in enumerate(self._tokenized_docs):
            score = self._score(query_tokens, doc_tokens, i)
            if score > 0:
                scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in scores[:top_k]:
            doc = self.documents[idx]
            results.append(
                {
                    "id": doc.id,
                    "text": doc.text,
                    "score": score,
                    "metadata": doc.metadata,
                }
            )

        return results

    def _score(self, query_tokens: list[str], doc_tokens: list[str], doc_idx: int) -> float:
        doc_len = self.doc_lens[doc_idx]
        token_counts = Counter(doc_tokens)

        score = 0.0
        for token in query_tokens:
            if token not in self.doc_freqs:
                continue

            tf = token_counts.get(token, 0)
            if tf == 0:
                continue

            df = self.doc_freqs[token]
            n = len(self.documents)

            idf = math.log((n - df + 0.5) / (df + 0.5) + 1)

            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)

            score += idf * numerator / denominator

        return score

    def clear(self) -> None:
        self.documents = []
        self.doc_freqs = {}
        self.doc_lens = []
        self.avgdl = 0
        self._tokenized_docs = []


def create_bm25_retriever(**kwargs) -> BM25Retriever:
    return BM25Retriever(**kwargs)

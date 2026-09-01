from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.config.logging import get_logger
from app.retrieval.embeddings import EmbeddingProvider, create_embedding_provider

logger = get_logger(__name__)


@dataclass
class VectorDocument:
    id: str
    text: str
    embedding: list[float] | None = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class VectorStore(ABC):
    @abstractmethod
    async def add_documents(self, documents: list[VectorDocument]) -> None:
        pass

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def delete(self, ids: list[str]) -> None:
        pass

    @abstractmethod
    async def get(self, id: str) -> VectorDocument | None:
        pass

    @abstractmethod
    def count(self) -> int:
        pass


class InMemoryVectorStore(VectorStore):
    def __init__(self, embedding_provider: EmbeddingProvider | None = None):
        self.embedding_provider = embedding_provider or create_embedding_provider()
        self.documents: dict[str, VectorDocument] = {}
        self.embeddings: dict[str, list[float]] = {}

    async def add_documents(self, documents: list[VectorDocument]) -> None:
        for doc in documents:
            if doc.embedding is None:
                doc.embedding = await self.embedding_provider.embed_query(doc.text)

            self.documents[doc.id] = doc
            self.embeddings[doc.id] = doc.embedding

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        import numpy as np

        if not self.embeddings:
            return []

        doc_ids = list(self.embeddings.keys())
        doc_embeddings = np.array([self.embeddings[doc_id] for doc_id in doc_ids])
        query_arr = np.array(query_embedding)

        similarities = np.dot(doc_embeddings, query_arr) / (
            np.linalg.norm(doc_embeddings, axis=1) * np.linalg.norm(query_arr) + 1e-8
        )

        results = []
        for idx, score in enumerate(similarities):
            doc_id = doc_ids[idx]
            doc = self.documents[doc_id]

            if filter and not self._matches_filter(doc.metadata, filter):
                continue

            results.append(
                {
                    "id": doc_id,
                    "text": doc.text,
                    "score": float(score),
                    "metadata": doc.metadata,
                }
            )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _matches_filter(self, metadata: dict[str, Any], filter: dict[str, Any]) -> bool:
        for key, value in filter.items():
            if key not in metadata:
                return False
            if isinstance(value, list):
                if metadata[key] not in value:
                    return False
            elif metadata[key] != value:
                return False
        return True

    async def delete(self, ids: list[str]) -> None:
        for doc_id in ids:
            self.documents.pop(doc_id, None)
            self.embeddings.pop(doc_id, None)

    async def get(self, id: str) -> VectorDocument | None:
        return self.documents.get(id)

    def count(self) -> int:
        return len(self.documents)


class PGVectorStore(VectorStore):
    def __init__(
        self,
        connection_string: str,
        table_name: str = "embeddings",
        embedding_provider: EmbeddingProvider | None = None,
    ):
        self.connection_string = connection_string
        self.table_name = table_name
        self.embedding_provider = embedding_provider or create_embedding_provider()
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg

            self._pool = await asyncpg.create_pool(self.connection_string)
        return self._pool

    async def add_documents(self, documents: list[VectorDocument]) -> None:
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            for doc in documents:
                if doc.embedding is None:
                    doc.embedding = await self.embedding_provider.embed_query(doc.text)

                await conn.execute(
                    f"""
                    INSERT INTO {self.table_name} (id, text, embedding, metadata)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (id) DO UPDATE SET
                        text = EXCLUDED.text,
                        embedding = EXCLUDED.embedding,
                        metadata = EXCLUDED.metadata
                    """,
                    doc.id,
                    doc.text,
                    doc.embedding,
                    doc.metadata,
                )

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        pool = await self._get_pool()

        filter_clause = ""
        filter_params = []

        if filter:
            conditions = []
            for i, (key, value) in enumerate(filter.items(), 1):
                conditions.append(f"metadata->>'{key}' = ${i + 1}")
                filter_params.append(str(value))
            filter_clause = "WHERE " + " AND ".join(conditions)

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT id, text, embedding, metadata,
                       1 - (embedding <=> $1) as similarity
                FROM {self.table_name}
                {filter_clause}
                ORDER BY embedding <=> $1
                LIMIT $2
                """,
                query_embedding,
                top_k,
                *filter_params,
            )

        return [
            {
                "id": row["id"],
                "text": row["text"],
                "score": row["similarity"],
                "metadata": row["metadata"],
            }
            for row in rows
        ]

    async def delete(self, ids: list[str]) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                f"DELETE FROM {self.table_name} WHERE id = ANY($1)",
                ids,
            )

    async def get(self, id: str) -> VectorDocument | None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT id, text, embedding, metadata FROM {self.table_name} WHERE id = $1",
                id,
            )
            if row:
                return VectorDocument(
                    id=row["id"],
                    text=row["text"],
                    embedding=row["embedding"],
                    metadata=row["metadata"],
                )
        return None

    def count(self) -> int:
        return 0


class PineconeVectorStore(VectorStore):
    def __init__(
        self,
        api_key: str,
        index_name: str,
        environment: str = "us-east-1",
        embedding_provider: EmbeddingProvider | None = None,
    ):
        self.api_key = api_key
        self.index_name = index_name
        self.environment = environment
        self.embedding_provider = embedding_provider or create_embedding_provider()
        self._index = None

    async def _get_index(self):
        if self._index is None:
            try:
                import pinecone

                pinecone.init(api_key=self.api_key, environment=self.environment)
                self._index = pinecone.Index(self.index_name)
            except ImportError:
                logger.error("pinecone_not_installed")
                raise

    async def add_documents(self, documents: list[VectorDocument]) -> None:
        index = await self._get_index()

        vectors = []
        for doc in documents:
            if doc.embedding is None:
                doc.embedding = await self.embedding_provider.embed_query(doc.text)

            vectors.append(
                {
                    "id": doc.id,
                    "values": doc.embedding,
                    "metadata": {**doc.metadata, "text": doc.text},
                }
            )

        index.upsert(vectors=vectors)

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        index = await self._get_index()

        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            filter=filter,
            include_metadata=True,
        )

        return [
            {
                "id": match["id"],
                "text": match["metadata"].get("text", ""),
                "score": match["score"],
                "metadata": {k: v for k, v in match["metadata"].items() if k != "text"},
            }
            for match in results["matches"]
        ]

    async def delete(self, ids: list[str]) -> None:
        index = await self._get_index()
        index.delete(ids=ids)

    async def get(self, id: str) -> VectorDocument | None:
        index = await self._get_index()
        result = index.fetch(ids=[id])

        if id in result["vectors"]:
            vec = result["vectors"][id]
            return VectorDocument(
                id=id,
                text=vec["metadata"].get("text", ""),
                embedding=vec["values"],
                metadata={k: v for k, v in vec["metadata"].items() if k != "text"},
            )
        return None

    def count(self) -> int:
        index = self._index
        if index:
            stats = index.describe_index_stats()
            return stats.get("total_vector_count", 0)
        return 0


def create_vector_store(provider: str = "memory", **kwargs) -> VectorStore:
    if provider == "memory":
        return InMemoryVectorStore(**kwargs)
    elif provider == "pgvector":
        return PGVectorStore(**kwargs)
    elif provider == "pinecone":
        return PineconeVectorStore(**kwargs)
    else:
        raise ValueError(f"Unknown vector store provider: {provider}")

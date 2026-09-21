import json
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
        connection_string: str | None = None,
        table_name: str = "document_chunks",
        embedding_provider: EmbeddingProvider | None = None,
        session: Any = None,
    ):
        from app.config.settings import get_settings

        settings = get_settings()
        self.connection_string = connection_string or settings.DATABASE_URL
        self.table_name = table_name
        self.embedding_provider = embedding_provider or create_embedding_provider()
        self.session = session
        self.dimension = self.embedding_provider.get_dimension()
        self._pool = None

    def _validate_dimension(self, embedding: list[float], context: str) -> None:
        if len(embedding) != self.dimension:
            raise ValueError(
                f"{context} embedding dimension mismatch: expected {self.dimension}, "
                f"got {len(embedding)}"
            )

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg

            # Clean connection string if it has +asyncpg driver prefix for SQLAlchemy
            conn_str = self.connection_string.replace("postgresql+asyncpg://", "postgresql://")
            self._pool = await asyncpg.create_pool(conn_str)
        return self._pool

    async def add_documents(self, documents: list[VectorDocument], session: Any = None) -> None:
        db_session = session or self.session

        for doc in documents:
            if doc.embedding is None:
                doc.embedding = await self.embedding_provider.embed_query(doc.text)
            self._validate_dimension(doc.embedding, "Document")

        if db_session is not None:
            from app.db.base import DocumentChunk

            for doc in documents:
                meta = doc.metadata or {}
                chunk_index = meta.get("chunk_index", 0)
                report_id = meta.get("report_id", doc.id)

                chunk = DocumentChunk(
                    id=doc.id,
                    report_id=str(report_id),
                    chunk_index=int(chunk_index),
                    content=doc.text,
                    token_count=len(doc.text.split()),
                    page_start=meta.get("start_page"),
                    page_end=meta.get("end_page"),
                    section_title=meta.get("section_title"),
                    embedding=doc.embedding,
                    metadata_=meta,
                )
                await db_session.merge(chunk)
            await db_session.commit()
            return

        pool = await self._get_pool()
        import json

        async with pool.acquire() as conn:
            for doc in documents:
                meta = doc.metadata or {}
                report_id = meta.get("report_id", doc.id)
                chunk_index = meta.get("chunk_index", 0)

                await conn.execute(
                    f"""
                    INSERT INTO {self.table_name} (
                        id, report_id, chunk_index, content, token_count,
                        page_start, page_end, section_title, embedding, metadata
                    )
                    VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, $7, $8, $9::vector, $10::jsonb)
                    ON CONFLICT (report_id, chunk_index) DO UPDATE SET
                        content = EXCLUDED.content,
                        token_count = EXCLUDED.token_count,
                        page_start = EXCLUDED.page_start,
                        page_end = EXCLUDED.page_end,
                        section_title = EXCLUDED.section_title,
                        embedding = EXCLUDED.embedding,
                        metadata = EXCLUDED.metadata
                    """,
                    str(doc.id),
                    str(report_id),
                    int(chunk_index),
                    doc.text,
                    len(doc.text.split()),
                    meta.get("start_page"),
                    meta.get("end_page"),
                    meta.get("section_title"),
                    str(doc.embedding) if doc.embedding else None,
                    json.dumps(meta),
                )

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
        session: Any = None,
    ) -> list[dict[str, Any]]:
        db_session = session or self.session
        self._validate_dimension(query_embedding, "Query")

        if db_session is not None:
            from sqlalchemy import select
            from app.db.base import DocumentChunk
            from app.retrieval.embeddings import batch_cosine_similarity

            stmt = select(DocumentChunk)
            if filter:
                if "report_id" in filter:
                    stmt = stmt.where(DocumentChunk.report_id == str(filter["report_id"]))
                if "company_id" in filter:
                    stmt = stmt.where(
                        DocumentChunk.metadata_["company_id"].as_string()
                        == str(filter["company_id"])
                    )
                if "fiscal_year" in filter:
                    stmt = stmt.where(
                        DocumentChunk.metadata_["fiscal_year"].as_string()
                        == str(filter["fiscal_year"])
                    )

            result = await db_session.execute(stmt)
            chunks = result.scalars().all()

            if not chunks:
                return []

            candidate_embeddings = []
            valid_chunks = []
            for c in chunks:
                if c.embedding is not None:
                    candidate_embeddings.append(c.embedding)
                    valid_chunks.append(c)

            if not valid_chunks:
                return []

            scores = batch_cosine_similarity(query_embedding, candidate_embeddings)
            results = []
            for chunk, score in zip(valid_chunks, scores, strict=True):
                stored_metadata = chunk.metadata_ or {}
                meta = {
                    "report_id": str(chunk.report_id),
                    "chunk_index": chunk.chunk_index,
                    "start_page": chunk.page_start,
                    "end_page": chunk.page_end,
                    "section_title": chunk.section_title,
                    **stored_metadata,
                }

                # Apply remaining metadata filters if present
                if filter:
                    match = True
                    for k, v in filter.items():
                        if k in ("company_id", "report_id", "fiscal_year"):
                            continue
                        if meta.get(k) != v:
                            match = False
                            break
                    if not match:
                        continue

                results.append({
                    "id": str(chunk.id),
                    "text": chunk.content,
                    "score": float(score),
                    "metadata": meta,
                })

            results.sort(key=lambda x: float(x["score"]), reverse=True)
            return results[:top_k]

        pool = await self._get_pool()
        filter_clause = ""
        filter_params = []

        if filter:
            conditions = []
            idx = 2
            for key, value in filter.items():
                if key in ("company_id", "report_id", "fiscal_year"):
                    if key == "report_id":
                        conditions.append(f"{key} = ${idx}")
                    else:
                        conditions.append(f"metadata->>'{key}' = ${idx}")
                    filter_params.append(str(value))
                else:
                    conditions.append(f"metadata->>'{key}' = ${idx}")
                    filter_params.append(str(value))
                idx += 1
            if conditions:
                filter_clause = "WHERE " + " AND ".join(conditions)

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                  SELECT id, content, embedding, metadata,
                      report_id, chunk_index, page_start, page_end, section_title,
                       1 - (embedding <=> $1::vector) as similarity
                FROM {self.table_name}
                {filter_clause}
                ORDER BY embedding <=> $1::vector
                LIMIT ${len(filter_params) + 2}
                """,
                str(query_embedding),
                *filter_params,
                top_k,
            )

        return [
            {
                "id": str(row["id"]),
                "text": row["content"],
                "score": float(row["similarity"]) if row["similarity"] is not None else 0.0,
                "metadata": {
                    "report_id": str(row["report_id"]),
                    "chunk_index": row["chunk_index"],
                    "start_page": row["page_start"],
                    "end_page": row["page_end"],
                    "section_title": row["section_title"],
                    **(json.loads(row["metadata"]) if isinstance(row["metadata"], str) else (row["metadata"] or {})),
                },
            }
            for row in rows
        ]

    async def delete(self, ids: list[str], session: Any = None) -> None:
        db_session = session or self.session
        if db_session is not None:
            from sqlalchemy import delete
            from app.db.base import DocumentChunk

            stmt = delete(DocumentChunk).where(DocumentChunk.id.in_([str(i) for i in ids]))
            await db_session.execute(stmt)
            await db_session.commit()
            return

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                f"DELETE FROM {self.table_name} WHERE id = ANY($1::uuid[])",
                [str(i) for i in ids],
            )

    async def get(self, id: str, session: Any = None) -> VectorDocument | None:
        db_session = session or self.session
        if db_session is not None:
            from app.db.base import DocumentChunk

            chunk = await db_session.get(DocumentChunk, str(id))
            if chunk:
                return VectorDocument(
                    id=str(chunk.id),
                    text=chunk.content,
                    embedding=chunk.embedding,
                    metadata={
                        "report_id": str(chunk.report_id),
                        "chunk_index": chunk.chunk_index,
                        "start_page": chunk.page_start,
                        "end_page": chunk.page_end,
                        "section_title": chunk.section_title,
                        **(chunk.metadata_ or {}),
                    },
                )
            return None

        pool = await self._get_pool()
        import json

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""SELECT id, content, embedding, metadata, report_id,
                           chunk_index, page_start, page_end, section_title
                    FROM {self.table_name} WHERE id = $1::uuid""",
                str(id),
            )
            if row:
                extra_meta = json.loads(row["metadata"]) if isinstance(row["metadata"], str) else (row["metadata"] or {})
                return VectorDocument(
                    id=str(row["id"]),
                    text=row["content"],
                    embedding=row["embedding"],
                    metadata={
                        "report_id": str(row["report_id"]),
                        "chunk_index": row["chunk_index"],
                        "start_page": row["page_start"],
                        "end_page": row["page_end"],
                        "section_title": row["section_title"],
                        **extra_meta,
                    },
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

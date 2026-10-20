import hashlib
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logging import get_logger
from app.db.base import DocumentChunk
from app.processing.chunker import TextChunk, chunk_document, tokenize
from app.retrieval.embeddings import EmbeddingProvider, create_embedding_provider
from app.retrieval.vector_store import PGVectorStore, VectorDocument

logger = get_logger(__name__)


class EmbeddingPipeline:
    """End-to-end pipeline connecting chunking -> embedding generation -> vector storage in PostgreSQL (pgvector)."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider | None = None,
        vector_store: PGVectorStore | None = None,
    ):
        self.embedding_provider = embedding_provider or create_embedding_provider()
        self.vector_store = vector_store or PGVectorStore(embedding_provider=self.embedding_provider)

    async def process_and_store_chunks(
        self,
        db: AsyncSession,
        report_id: UUID | str,
        company_id: UUID | str,
        fiscal_year: int,
        text_or_pages: str | list[str],
        strategy: str = "fixed",
        force_reprocess: bool = False,
    ) -> list[DocumentChunk]:
        """Chunks document text/pages, computes embeddings, and persists DocumentChunk records to PostgreSQL."""
        rep_id_str = str(report_id)
        comp_id_str = str(company_id)

        # Check existing chunks to avoid redundant embedding generation if not forcing reprocess
        if not force_reprocess:
            existing = await db.execute(
                select(DocumentChunk).where(DocumentChunk.report_id == rep_id_str)
            )
            existing_chunks = existing.scalars().all()
            if existing_chunks:
                logger.info(
                    "chunks_already_exist",
                    report_id=rep_id_str,
                    count=len(existing_chunks),
                )
                return list(existing_chunks)

        # 1. Chunking step
        if isinstance(text_or_pages, list):
            chunks: list[TextChunk] = chunk_document(
                text="", pages=text_or_pages, strategy=strategy
            )
        else:
            chunks: list[TextChunk] = chunk_document(
                text=text_or_pages, strategy=strategy
            )

        if not chunks:
            logger.warning("no_chunks_generated", report_id=rep_id_str)
            return []

        # 2. Embedding generation step
        texts = [chunk.text for chunk in chunks]
        embeddings = await self.embedding_provider.embed(texts)
        expected_dimension = self.embedding_provider.get_dimension()
        for index, embedding in enumerate(embeddings):
            if len(embedding) != expected_dimension:
                raise ValueError(
                    f"Embedding dimension mismatch at chunk {index}: expected {expected_dimension}, "
                    f"got {len(embedding)}"
                )
        model_name = self.embedding_provider.get_model_name()

        # Delete old chunks if force_reprocess is True
        if force_reprocess:
            await db.execute(
                delete(DocumentChunk).where(DocumentChunk.report_id == rep_id_str)
            )

        # 3. Vector persistence step via ORM DocumentChunk
        chunk_records: list[DocumentChunk] = []
        vector_docs: list[VectorDocument] = []

        for chunk, emb in zip(chunks, embeddings, strict=True):
            chunk_id = str(uuid4())
            chunk_hash = hashlib.sha256(chunk.text.encode()).hexdigest()[:16]

            meta = {
                "report_id": rep_id_str,
                "company_id": comp_id_str,
                "fiscal_year": fiscal_year,
                "chunk_index": chunk.chunk_index,
                "chunk_hash": chunk_hash,
                "start_page": chunk.start_page,
                "end_page": chunk.end_page,
                "section_title": chunk.section_title,
            }

            db_chunk = DocumentChunk(
                id=chunk_id,
                report_id=rep_id_str,
                chunk_index=chunk.chunk_index,
                content=chunk.text,
                token_count=len(tokenize(chunk.text)),
                page_start=chunk.start_page,
                page_end=chunk.end_page,
                section_title=chunk.section_title,
                embedding=emb,
                metadata_={
                    **(chunk.metadata or {}),
                    "company_id": comp_id_str,
                    "fiscal_year": fiscal_year,
                    "chunk_hash": chunk_hash,
                    "embedding_model": model_name,
                },
            )
            chunk_records.append(db_chunk)

            vector_docs.append(
                VectorDocument(
                    id=chunk_id,
                    text=chunk.text,
                    embedding=emb,
                    metadata=meta,
                )
            )

        db.add_all(chunk_records)
        await db.commit()

        logger.info(
            "chunks_embedded_and_stored",
            report_id=rep_id_str,
            count=len(chunk_records),
            model=model_name,
            dimension=self.embedding_provider.get_dimension(),
        )

        return chunk_records

    async def search_similar_chunks(
        self,
        db: AsyncSession,
        query: str,
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Vector similarity search against document chunks stored in PostgreSQL."""
        query_embedding = await self.embedding_provider.embed_query(query)
        return await self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            filter=filter,
            session=db,
        )


def create_embedding_pipeline(
    embedding_provider: EmbeddingProvider | None = None,
    vector_store: PGVectorStore | None = None,
) -> EmbeddingPipeline:
    return EmbeddingPipeline(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

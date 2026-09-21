import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.db.base import Company, DocumentChunk, Report
from app.processing.chunker import TextChunk, chunk_document
from app.retrieval.embedding_pipeline import EmbeddingPipeline, create_embedding_pipeline
from app.retrieval.embeddings import SentenceTransformersEmbedding, create_embedding_provider
from app.retrieval.vector_store import PGVectorStore, VectorDocument


class MockEmbeddingProvider:
    """Mock embedding provider for deterministic testing without external dependencies."""

    def __init__(self, dimension: int = 1024, model_name: str = "mock-embedding-v1"):
        self.dimension = dimension
        self.model_name = model_name

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # Deterministic pseudo-embeddings based on text length and ascii sums
        results = []
        for text in texts:
            val = float(sum(ord(c) for c in text) % 100) / 100.0
            vec = [val] * self.dimension
            results.append(vec)
        return results

    async def embed_query(self, text: str) -> list[float]:
        val = float(sum(ord(c) for c in text) % 100) / 100.0
        return [val] * self.dimension

    def get_dimension(self) -> int:
        return self.dimension

    def get_model_name(self) -> str:
        return self.model_name


class MismatchedEmbeddingProvider(MockEmbeddingProvider):
    def __init__(self, declared_dimension: int, actual_dimension: int):
        super().__init__(dimension=declared_dimension)
        self.actual_dimension = actual_dimension

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * self.actual_dimension for _ in texts]

    async def embed_query(self, text: str) -> list[float]:
        return [0.1] * self.actual_dimension


# ---------------------------------------------------------------------------
# 1. Embedding Provider & Dimension Tests
# ---------------------------------------------------------------------------

def test_embedding_provider_dimension_config():
    """Verify configured embedding dimension programmatically matches settings."""
    settings = get_settings()
    provider = SentenceTransformersEmbedding()
    assert provider.get_dimension() == settings.EMBEDDING_DIMENSION
    assert provider.get_dimension() == 1024
    assert provider.get_model_name() == "BAAI/bge-large-en-v1.5"


def test_create_embedding_provider_factory():
    """Verify provider factory returns configured embedding provider."""
    provider = create_embedding_provider()
    assert isinstance(provider, SentenceTransformersEmbedding)
    assert provider.get_dimension() == 1024
    assert provider.get_model_name() == "BAAI/bge-large-en-v1.5"


@pytest.mark.asyncio
async def test_sentence_transformers_rejects_actual_dimension_mismatch():
    provider = SentenceTransformersEmbedding()

    class FakeModel:
        def encode(self, texts, **kwargs):
            import numpy as np

            return np.zeros((len(texts), 1536), dtype=float)

    provider._model = FakeModel()

    with pytest.raises(ValueError, match="expected 1024, got 1536"):
        await provider.embed_query("test")


# ---------------------------------------------------------------------------
# 2. Chunking & Embedding Conversion Unit Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chunk_to_embedding_conversion():
    """Verify text document is chunked and converted into vector embeddings correctly."""
    sample_text = (
        "The company is exposed to significant operational risks due to legacy IT systems. "
        "Cybersecurity breaches could disrupt operations and lead to regulatory fines. "
        "Foreign exchange fluctuations impact international revenue margins."
    )
    chunks: list[TextChunk] = chunk_document(sample_text, strategy="fixed", chunk_size=100)
    assert len(chunks) > 0

    mock_provider = MockEmbeddingProvider(dimension=1024)
    embeddings = await mock_provider.embed([c.text for c in chunks])

    assert len(embeddings) == len(chunks)
    assert len(embeddings[0]) == 1024


# ---------------------------------------------------------------------------
# 3. DocumentChunk Model & Database Persistence Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_document_chunk_orm_persistence(db_session: AsyncSession):
    """Verify DocumentChunk SQLAlchemy model persists to the database correctly."""
    company_id = str(uuid.uuid4())
    report_id = str(uuid.uuid4())

    company = Company(
        id=company_id,
        name="Vector Test Corp",
        sector="Technology",
    )
    report = Report(
        id=report_id,
        company_id=company_id,
        fiscal_year=2024,
        source_file="annual_report_2024.pdf",
        processing_status="processing",
    )
    db_session.add(company)
    db_session.add(report)
    await db_session.commit()

    mock_embedding = [0.1] * 1024
    chunk = DocumentChunk(
        id=str(uuid.uuid4()),
        report_id=report_id,
        chunk_index=0,
        content="Sample chunk content for risk assessment",
        token_count=6,
        page_start=1,
        page_end=1,
        embedding=mock_embedding,
        metadata_={"section": "Risk Factors"},
    )
    db_session.add(chunk)
    await db_session.commit()

    saved_chunk = await db_session.get(DocumentChunk, chunk.id)
    assert saved_chunk is not None
    assert saved_chunk.report_id == report_id
    assert saved_chunk.chunk_index == 0
    assert saved_chunk.content == "Sample chunk content for risk assessment"
    assert saved_chunk.metadata_ == {"section": "Risk Factors"}


# ---------------------------------------------------------------------------
# 4. Vector Store Insertion, Search & Metadata Filtering Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pgvector_store_with_session(db_session: AsyncSession):
    """Verify PGVectorStore search and metadata filtering using AsyncSession."""
    mock_provider = MockEmbeddingProvider(dimension=1024)
    store = PGVectorStore(embedding_provider=mock_provider, session=db_session)

    comp_a = str(uuid.uuid4())
    comp_b = str(uuid.uuid4())
    rep_a = str(uuid.uuid4())
    rep_b = str(uuid.uuid4())

    doc1 = VectorDocument(
        id=str(uuid.uuid4()),
        text="High cybersecurity threat from ransomware attacks",
        embedding=[1.0] * 1024,
        metadata={"company_id": comp_a, "report_id": rep_a, "fiscal_year": 2023, "chunk_index": 0},
    )
    doc2 = VectorDocument(
        id=str(uuid.uuid4()),
        text="Operational risk in supply chain logistics",
        embedding=[0.5] * 1024,
        metadata={"company_id": comp_b, "report_id": rep_b, "fiscal_year": 2024, "chunk_index": 0},
    )

    await store.add_documents([doc1, doc2], session=db_session)

    # Search with company_id filter
    results_a = await store.search(
        query_embedding=[1.0] * 1024,
        top_k=5,
        filter={"company_id": comp_a},
        session=db_session,
    )
    assert len(results_a) == 1
    assert results_a[0]["metadata"]["company_id"] == comp_a
    assert "cybersecurity" in results_a[0]["text"].lower()

    # Search across all documents
    results_all = await store.search(
        query_embedding=[1.0] * 1024,
        top_k=5,
        session=db_session,
    )
    assert len(results_all) == 2


# ---------------------------------------------------------------------------
# 5. End-to-End EmbeddingPipeline Test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_embedding_pipeline_end_to_end(db_session: AsyncSession):
    """Verify EmbeddingPipeline cleanly processes pages -> chunks -> embeddings -> DB store -> search."""
    comp_id = str(uuid.uuid4())
    rep_id = str(uuid.uuid4())

    mock_provider = MockEmbeddingProvider(dimension=1024)
    pipeline = create_embedding_pipeline(embedding_provider=mock_provider)

    sample_pages = [
        "Page 1: Overview of operations. Financial stability remains strong.",
        "Page 2: Item 1A. Risk Factors. Regulatory changes in EU privacy law may impact compliance costs.",
    ]

    stored_chunks = await pipeline.process_and_store_chunks(
        db=db_session,
        report_id=rep_id,
        company_id=comp_id,
        fiscal_year=2024,
        text_or_pages=sample_pages,
    )
    assert len(stored_chunks) > 0
    assert stored_chunks[0].report_id == rep_id
    assert stored_chunks[0].metadata_["fiscal_year"] == 2024

    # Perform vector search through pipeline
    search_results = await pipeline.search_similar_chunks(
        db=db_session,
        query="Regulatory changes in EU privacy law",
        top_k=3,
        filter={"company_id": comp_id},
    )
    assert len(search_results) > 0
    assert search_results[0]["metadata"]["company_id"] == comp_id


@pytest.mark.asyncio
async def test_embedding_pipeline_rejects_non_1024_vectors():
    """Reject incompatible vectors before any database insertion is attempted."""
    class EmptyResult:
        def scalars(self):
            return self

        def all(self):
            return []

    class NoWriteSession:
        async def execute(self, statement):
            return EmptyResult()

    pipeline = create_embedding_pipeline(
        embedding_provider=MismatchedEmbeddingProvider(
            declared_dimension=1024, actual_dimension=1536
        )
    )

    with pytest.raises(ValueError, match="expected 1024, got 1536"):
        await pipeline.process_and_store_chunks(
            db=NoWriteSession(),
            report_id=str(uuid.uuid4()),
            company_id=str(uuid.uuid4()),
            fiscal_year=2024,
            text_or_pages=[
                "A sufficiently long page contains operational risk information "
                "that must be embedded before it can be stored."
            ],
        )


@pytest.mark.asyncio
async def test_pgvector_store_rejects_incorrect_query_dimension():
    store = PGVectorStore(embedding_provider=MockEmbeddingProvider(dimension=1024))

    with pytest.raises(ValueError, match="expected 1024, got 1536"):
        await store.search(query_embedding=[0.1] * 1536)


# ---------------------------------------------------------------------------
# 6. Database Integration Note for Live Supabase pgvector
# ---------------------------------------------------------------------------

def test_supabase_pgvector_integration_status():
    """Integration note for the existing Supabase pgvector instance.

    Before running integration tests:
    1. Set SUPABASE DATABASE_URL in .env.
    2. Confirm the existing document_chunks table is vector(1024).
    3. Run integration tests against the existing table.
    """
    settings = get_settings()
    # Confirm fallback / configured settings are valid
    assert settings.VECTOR_STORE_PROVIDER in ("pgvector", "memory")

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, TypeDecorator, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# pgvector is an optional dependency.  The column type is only materialised
# when pgvector is installed; otherwise we fall back to Text so the module
# can still be imported and the InMemory path still works.
try:
    from pgvector.sqlalchemy import Vector as PgVector  # type: ignore

    _VECTOR_TYPE_AVAILABLE = True
except ImportError:  # pragma: no cover
    PgVector = None
    _VECTOR_TYPE_AVAILABLE = False


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        nullable=False,
    )


class Company(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    market_cap: Mapped[float | None] = mapped_column(nullable=True)
    listed_exchange: Mapped[str | None] = mapped_column(String(50), nullable=True)
    workspace_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        default=dict,
        server_default=text("'{}'"),
    )

    # Relationships
    reports: Mapped[list["Report"]] = relationship(
        "Report", back_populates="company", cascade="all, delete-orphan", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Company(id={self.id}, name={self.name}, sector={self.sector})>"


class _ReportProcessingStatus(TypeDecorator[str]):
    """Translate the app's completed/pending states to the deployed DB vocabulary."""

    impl = String(50)
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        if value == "completed":
            return "processed"
        if value == "pending":
            return "queued"
        return value

    def process_result_value(self, value: str | None, dialect) -> str | None:
        return "completed" if value == "processed" else value


class Report(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "reports"

    company_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    fiscal_year: Mapped[int] = mapped_column(nullable=False, index=True)
    upload_date: Mapped[datetime] = mapped_column(
        "uploaded_at", DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    report_type: Mapped[str] = mapped_column(String(100), nullable=False, default="annual_report")
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_file_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    uploaded_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    processing_status: Mapped[str] = mapped_column(
        _ReportProcessingStatus(), nullable=False, default="pending", index=True
    )
    source_file: Mapped[str | None] = mapped_column("source_file_path", Text, nullable=True)
    source_file_hash: Mapped[str | None] = mapped_column("file_hash", String(64), nullable=True)
    pages: Mapped[int | None] = mapped_column("page_count", nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        default=dict,
        server_default=text("'{}'"),
    )
    error_message: Mapped[str | None] = mapped_column("processing_error", Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="reports", lazy="noload")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="report", cascade="all, delete-orphan", lazy="noload"
    )

    def __repr__(self) -> str:
        return (
            f"<Report(id={self.id}, company_id={self.company_id}, "
            f"year={self.fiscal_year}, status={self.processing_status})>"
        )


class RiskItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "risk_items"

    report_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    confidence_score: Mapped[float] = mapped_column(nullable=False, default=0.0)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_page: Mapped[int | None] = mapped_column(nullable=True)
    source_paragraph: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_text_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entities: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)

    def __repr__(self) -> str:
        return (
            f"<RiskItem(id={self.id}, category={self.category}, "
            f"severity={self.severity}, confidence={self.confidence_score})>"
        )


class EvolutionEntry(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "evolution_entries"

    risk_item_id_prev: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), nullable=True, index=True
    )
    risk_item_id_current: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), nullable=True, index=True
    )
    change_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    similarity_score: Mapped[float | None] = mapped_column(nullable=True)
    severity_change: Mapped[int | None] = mapped_column(nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)

    def __repr__(self) -> str:
        return (
            f"<EvolutionEntry(id={self.id}, change_type={self.change_type}, "
            f"prev={self.risk_item_id_prev}, current={self.risk_item_id_current})>"
        )


class FinancialSnapshot(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "financial_snapshots"

    company_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    fiscal_year: Mapped[int] = mapped_column(nullable=False, index=True)
    revenue: Mapped[float | None] = mapped_column(nullable=True)
    profit: Mapped[float | None] = mapped_column(nullable=True)
    net_margin: Mapped[float | None] = mapped_column(nullable=True)
    roe: Mapped[float | None] = mapped_column(nullable=True)
    roce: Mapped[float | None] = mapped_column(nullable=True)
    eps: Mapped[float | None] = mapped_column(nullable=True)
    debt_equity: Mapped[float | None] = mapped_column(nullable=True)
    cash_flow: Mapped[float | None] = mapped_column(nullable=True)
    market_cap: Mapped[float | None] = mapped_column(nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)

    def __repr__(self) -> str:
        return (
            f"<FinancialSnapshot(id={self.id}, company_id={self.company_id}, "
            f"year={self.fiscal_year})>"
        )


class Workspace(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)

    def __repr__(self) -> str:
        return f"<Workspace(id={self.id}, name={self.name})>"


class SavedScan(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "saved_scans"

    workspace_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    filter_conditions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    logic: Mapped[str] = mapped_column(String(10), nullable=False, default="AND")
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)

    def __repr__(self) -> str:
        return f"<SavedScan(id={self.id}, name={self.name}, workspace_id={self.workspace_id})>"


# ---------------------------------------------------------------------------
# DocumentChunk — stores individual text chunks + their pgvector embeddings.
# The embedding column uses pgvector when available; falls back to Text so
# the module stays importable without the extension for unit-test purposes.
# ---------------------------------------------------------------------------

def _embedding_column() -> "MappedColumn":  # type: ignore[type-arg]
    """Return the appropriate SQLAlchemy column type for embeddings."""
    if _VECTOR_TYPE_AVAILABLE and PgVector is not None:
        return mapped_column(PgVector(1024), nullable=True)
    # Fallback: store as JSON array so we can still run without pgvector.
    return mapped_column(JSON, nullable=True)


class DocumentChunk(Base, UUIDMixin):
    """A text chunk derived from a Report, with its vector embedding."""

    __tablename__ = "document_chunks"
    report_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    # The existing Supabase column is an unconstrained pgvector vector.
    embedding = _embedding_column()
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship
    report: Mapped["Report"] = relationship("Report", back_populates="chunks", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<DocumentChunk(id={self.id}, report_id={self.report_id}, "
            f"chunk_index={self.chunk_index}, page_start={self.page_start})>"
        )

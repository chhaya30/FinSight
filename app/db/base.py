from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, TypeDecorator, func, text, CheckConstraint, Date
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

try:
    from pgvector.sqlalchemy import Vector as PgVector
    _VECTOR_TYPE_AVAILABLE = True
except ImportError:
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
    __table_args__ = (
        CheckConstraint(
            "listed_exchange IS NULL OR listed_exchange IN ('NSE','BSE','NYSE','NASDAQ','LSE','OTHER')",
            name="companies_listed_exchange_check",
        ),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    legal_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    ticker_symbol: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    isin: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cin: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sub_industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    headquarters: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="India")
    listed_exchange: Mapped[str | None] = mapped_column(String(50), nullable=True)
    market_cap: Mapped[float | None] = mapped_column(nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    website_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    workspace_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        default=dict,
        server_default=text("'{}'"),
    )

    reports: Mapped[list["Report"]] = relationship(
        "Report", back_populates="company", cascade="all, delete-orphan", lazy="noload"
    )
    risks: Mapped[list["RiskItem"]] = relationship(
        "RiskItem", back_populates="company", lazy="noload"
    )
    financial_snapshots: Mapped[list["FinancialSnapshot"]] = relationship(
        "FinancialSnapshot", back_populates="company", lazy="noload"
    )
    financial_metrics: Mapped[list["FinancialMetric"]] = relationship(
        "FinancialMetric", back_populates="company", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Company(id={self.id}, name={self.name}, ticker={self.ticker_symbol})>"


class ReportProcessingStatus(TypeDecorator[str]):
    """Map PRD statuses to Supabase-compatible stored values."""
    impl = String(50)
    cache_ok = True

    _TO_DB = {
        "uploaded": "uploaded",
        "processing": "processing",
        "completed": "processed",
        "failed": "failed",
        "pending": "queued",
        "queued": "queued",
    }

    _FROM_DB = {
        "uploaded": "uploaded",
        "queued": "pending",
        "processing": "processing",
        "ocr_required": "processing",
        "processed": "completed",
        "failed": "failed",
        "cancelled": "failed",
    }

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        return self._TO_DB.get(value, value)

    def process_result_value(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        return self._FROM_DB.get(value, value)


class Report(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint(
            "report_type IN ('annual_report','10-K','20-F','10-Q','SEBI_FILING','BSE_FILING','NSE_FILING','OTHER')",
            name="reports_report_type_check",
        ),
        CheckConstraint(
            "processing_status IN ('uploaded','queued','processing','ocr_required','processed','failed','cancelled')",
            name="reports_processing_status_check",
        ),
    )

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
    report_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="annual_report",
    )
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_file_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_file: Mapped[str | None] = mapped_column("source_file_path", Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    file_size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    pages: Mapped[int | None] = mapped_column("page_count", nullable=True)
    document_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    uploaded_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    processing_status: Mapped[str] = mapped_column(
        ReportProcessingStatus(), nullable=False, default="uploaded", index=True
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def error_message(self) -> str | None:
        return self.processing_error

    @error_message.setter
    def error_message(self, value: str | None) -> None:
        self.processing_error = value

    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        default=dict,
        server_default=text("'{}'"),
    )

    company: Mapped["Company"] = relationship("Company", back_populates="reports", lazy="noload")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="report", cascade="all, delete-orphan", lazy="noload"
    )
    report_pages: Mapped[list["ReportPage"]] = relationship(
        "ReportPage", back_populates="report", cascade="all, delete-orphan", lazy="noload"
    )
    risks: Mapped[list["RiskItem"]] = relationship(
        "RiskItem", back_populates="report", cascade="all, delete-orphan", lazy="noload"
    )

    def __repr__(self) -> str:
        return (
            f"<Report(id={self.id}, company_id={self.company_id}, "
            f"year={self.fiscal_year}, status={self.processing_status})>"
        )


class RiskCategory(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "risk_categories"
    __table_args__ = (
        CheckConstraint(
            "default_severity IS NULL OR (default_severity >= 1 AND default_severity <= 5)",
            name="risk_categories_default_severity_check",
        ),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    default_severity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    risks: Mapped[list["RiskItem"]] = relationship("RiskItem", back_populates="category_rel", lazy="noload")

    def __repr__(self) -> str:
        return f"<RiskCategory(id={self.id}, name={self.name})>"


class ReportPage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "report_pages"

    report_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(nullable=True)
    layout_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )

    report: Mapped["Report"] = relationship("Report", back_populates="report_pages", lazy="noload")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="page", lazy="noload"
    )
    citations: Mapped[list["RiskCitation"]] = relationship(
        "RiskCitation", back_populates="page", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<ReportPage(report_id={self.report_id}, page={self.page_number})>"


def _embedding_column():
    if _VECTOR_TYPE_AVAILABLE and PgVector is not None:
        return mapped_column(PgVector(1024), nullable=True)
    return mapped_column(JSON, nullable=True)


class DocumentChunk(Base, UUIDMixin):
    __tablename__ = "document_chunks"

    report_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("report_pages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    company_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    fiscal_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding = _embedding_column()
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    report: Mapped["Report"] = relationship("Report", back_populates="chunks", lazy="noload")
    page: Mapped["ReportPage | None"] = relationship("ReportPage", back_populates="chunks", lazy="noload")
    citations: Mapped[list["RiskCitation"]] = relationship(
        "RiskCitation", back_populates="chunk", lazy="noload"
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentChunk(id={self.id}, report_id={self.report_id}, "
            f"chunk_index={self.chunk_index}, page_start={self.page_start})>"
        )


class RiskItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "risk_items"
    __table_args__ = (
        CheckConstraint("severity >= 1 AND severity <= 5", name="risk_items_severity_check"),
        CheckConstraint(
            "severity_label IS NULL OR severity_label IN ('LOW','MEDIUM','HIGH','CRITICAL')",
            name="risk_items_severity_label_check",
        ),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="risk_items_confidence_score_check",
        ),
        CheckConstraint(
            "extraction_method IS NULL OR extraction_method IN ('LLM','RULE','HYBRID','HUMAN')",
            name="risk_items_extraction_method_check",
        ),
        CheckConstraint(
            "review_status IN ('pending','reviewed','approved','rejected')",
            name="risk_items_review_status_check",
        ),
    )

    report_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("risk_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    risk_title: Mapped[str] = mapped_column(Text, nullable=False)
    risk_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    importance_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    severity_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confidence_score: Mapped[float] = mapped_column(nullable=False, default=0.0)
    materiality_score: Mapped[float | None] = mapped_column(nullable=True)
    is_material: Mapped[bool] = mapped_column(nullable=False, default=False)
    extraction_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    source_page: Mapped[int | None] = mapped_column(nullable=True)
    source_paragraph: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_text_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entities: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    embedding = _embedding_column()
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)

    report: Mapped["Report"] = relationship("Report", back_populates="risks", lazy="noload")
    company: Mapped["Company"] = relationship("Company", back_populates="risks", lazy="noload")
    category_rel: Mapped["RiskCategory | None"] = relationship("RiskCategory", back_populates="risks", lazy="noload")
    citations: Mapped[list["RiskCitation"]] = relationship(
        "RiskCitation", back_populates="risk", cascade="all, delete-orphan", lazy="noload"
    )
    entities_rel: Mapped[list["RiskEntity"]] = relationship(
        "RiskEntity", back_populates="risk", cascade="all, delete-orphan", lazy="noload"
    )

    def __repr__(self) -> str:
        return (
            f"<RiskItem(id={self.id}, category={self.category}, "
            f"severity={self.severity}, confidence={self.confidence_score})>"
        )


class RiskCitation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "risk_citations"
    __table_args__ = (
        CheckConstraint(
            "citation_type IN ('primary','supporting','contradicting')",
            name="risk_citations_citation_type_check",
        ),
    )

    risk_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("risk_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    page_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("report_pages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    paragraph_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    highlighted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_char: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_char: Mapped[int | None] = mapped_column(Integer, nullable=True)
    citation_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="primary"
    )
    relevance_score: Mapped[float | None] = mapped_column(nullable=True)

    risk: Mapped["RiskItem"] = relationship("RiskItem", back_populates="citations", lazy="noload")
    chunk: Mapped["DocumentChunk | None"] = relationship("DocumentChunk", back_populates="citations", lazy="noload")
    page: Mapped["ReportPage | None"] = relationship("ReportPage", back_populates="citations", lazy="noload")

    def __repr__(self) -> str:
        return f"<RiskCitation(risk_id={self.risk_id}, page={self.page_number})>"


class RiskEntity(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "risk_entities"

    risk_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("risk_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True, default=dict
    )

    risk: Mapped["RiskItem"] = relationship("RiskItem", back_populates="entities_rel", lazy="noload")

    def __repr__(self) -> str:
        return f"<RiskEntity(risk_id={self.risk_id}, type={self.entity_type}, name={self.entity_name})>"


class EvolutionEntry(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "evolution_entries"
    __table_args__ = (
        CheckConstraint(
            "change_type IN ('NEW','REMOVED','ESCALATED','DE-ESCALATED','MODIFIED','UNCHANGED')",
            name="evolution_entries_change_type_check",
        ),
    )

    risk_item_id_prev: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("risk_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    risk_item_id_current: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("risk_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    company_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    previous_report_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    current_report_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    change_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    similarity_score: Mapped[float | None] = mapped_column(nullable=True)
    severity_change: Mapped[int | None] = mapped_column(nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)

    def __repr__(self) -> str:
        return (
            f"<EvolutionEntry(id={self.id}, change_type={self.change_type}, "
            f"prev={self.risk_item_id_prev}, current={self.risk_item_id_current})>"
        )


class FinancialSnapshot(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "financial_snapshots"

    company_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    fiscal_year: Mapped[int] = mapped_column(nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    revenue: Mapped[float | None] = mapped_column(nullable=True)
    profit: Mapped[float | None] = mapped_column(nullable=True)
    net_margin: Mapped[float | None] = mapped_column(nullable=True)
    roe: Mapped[float | None] = mapped_column(nullable=True)
    roce: Mapped[float | None] = mapped_column(nullable=True)
    eps: Mapped[float | None] = mapped_column(nullable=True)
    debt_equity: Mapped[float | None] = mapped_column(nullable=True)
    cash_flow: Mapped[float | None] = mapped_column(nullable=True)
    operating_cash_flow: Mapped[float | None] = mapped_column(nullable=True)
    free_cash_flow: Mapped[float | None] = mapped_column(nullable=True)
    total_debt: Mapped[float | None] = mapped_column(nullable=True)
    total_assets: Mapped[float | None] = mapped_column(nullable=True)
    total_liabilities: Mapped[float | None] = mapped_column(nullable=True)
    market_cap: Mapped[float | None] = mapped_column(nullable=True)
    data_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    as_of_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    snapshot_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        default=dict,
        server_default=text("'{}'"),
    )

    company: Mapped["Company"] = relationship("Company", back_populates="financial_snapshots", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<FinancialSnapshot(id={self.id}, company_id={self.company_id}, "
            f"year={self.fiscal_year})>"
        )


class FinancialMetric(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "financial_metrics"

    company_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    fiscal_year: Mapped[int] = mapped_column(nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float | None] = mapped_column(nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    data_source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    company: Mapped["Company"] = relationship("Company", back_populates="financial_metrics", lazy="noload")

    def __repr__(self) -> str:
        return f"<FinancialMetric(company_id={self.company_id}, year={self.fiscal_year}, metric={self.metric_name})>"


class Workspace(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)

    def __repr__(self) -> str:
        return f"<Workspace(id={self.id}, name={self.name})>"


class SavedScan(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "saved_scans"
    __table_args__ = (
        CheckConstraint(
            "logic IN ('AND','OR')",
            name="saved_scans_logic_check",
        ),
    )

    workspace_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    created_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    filter_conditions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    logic: Mapped[str] = mapped_column(String(10), nullable=False, default="AND")
    is_shared: Mapped[bool] = mapped_column(nullable=False, default=False)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)

    def __repr__(self) -> str:
        return f"<SavedScan(id={self.id}, name={self.name}, workspace_id={self.workspace_id})>"
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)

    def __repr__(self) -> str:
        return f"<Company(id={self.id}, name={self.name}, sector={self.sector})>"


class Report(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "reports"

    company_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    fiscal_year: Mapped[int] = mapped_column(nullable=False, index=True)
    upload_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processing_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True
    )
    source_file: Mapped[str] = mapped_column(String(500), nullable=False)
    source_file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pages: Mapped[int | None] = mapped_column(nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

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

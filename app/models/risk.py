from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# from app.models.comparison import EvolutionEntryResponse
from app.models.document import DocumentResponse

if TYPE_CHECKING:
    from app.models.comparison import EvolutionEntryResponse
    from app.models.document import DocumentResponse


class RiskEntity(BaseModel):
    """Named entity extracted from risk text."""

    entity_type: str = Field(..., description="Type of entity: ORG, PERSON, GPE, MONEY, DATE, etc.")
    text: str
    start_char: int | None = None
    end_char: int | None = None
    confidence: float | None = Field(None, ge=0, le=1)


class RiskItemBase(BaseModel):
    report_id: UUID
    category: str = Field(..., max_length=100)
    severity: str = Field(..., max_length=50)
    confidence_score: float = Field(..., ge=0, le=1)
    summary: str = Field(..., min_length=1)
    source_page: int | None = Field(None, ge=1)
    source_paragraph: str | None = None
    source_text_hash: str | None = Field(None, max_length=64)
    entities: list[RiskEntity] | None = Field(default_factory=list)
    metadata: dict[str, Any] | None = Field(default_factory=dict)


class RiskItemCreate(RiskItemBase):
    pass


class RiskItemUpdate(BaseModel):
    category: str | None = Field(None, max_length=100)
    severity: str | None = Field(None, max_length=50)
    confidence_score: float | None = Field(None, ge=0, le=1)
    summary: str | None = None
    source_page: int | None = Field(None, ge=1)
    source_paragraph: str | None = None
    entities: list[RiskEntity] | None = None
    metadata: dict[str, Any] | None = None


class RiskItemResponse(RiskItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class RiskItemListResponse(BaseModel):
    risks: list[RiskItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class RiskItemDetailResponse(RiskItemResponse):
    evolution: Optional["EvolutionEntryResponse"] = None
    report: Optional["DocumentResponse"] = None


class RiskExtractionRequest(BaseModel):
    report_id: UUID
    force_reprocess: bool = False


class RiskExtractionResponse(BaseModel):
    report_id: UUID
    risks_extracted: int
    risks: list[RiskItemResponse]
    processing_time_seconds: float


class RiskEvidence(BaseModel):
    """Structured evidence representation preserving source document traceability."""

    document_id: str | None = None
    report_year: int | None = None
    page: int | None = Field(None, ge=1)
    chunk_id: str | None = None
    text: str = ""
    section: str | None = None
    text_hash: str | None = None
    char_start: int | None = None
    char_end: int | None = None
    context_before: str | None = None
    context_after: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizedRisk(BaseModel):
    """Canonical representation of an extracted risk across report years."""

    risk_id: str
    company_id: str | None = None
    report_id: str | None = None
    report_year: int = Field(..., ge=1900, le=2100)
    category: str = "Uncategorized"
    title: str
    description: str
    severity: str | None = None
    likelihood: str | None = None
    impact: str | None = None
    drivers: list[str] | None = Field(default_factory=list)
    affected_areas: list[str] | None = Field(default_factory=list)
    evidence: RiskEvidence | None = None
    source_page: int | None = Field(None, ge=1)
    confidence_score: float = Field(0.8, ge=0.0, le=1.0)
    embedding: list[float] | None = None
    extra_metadata: dict[str, Any] = Field(default_factory=dict)

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

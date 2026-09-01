from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.config.constants import ChangeType
from app.models.risk import RiskItemResponse


class EvolutionEntryBase(BaseModel):
    risk_item_id_prev: UUID | None = None
    risk_item_id_current: UUID | None = None
    change_type: ChangeType
    ai_summary: str | None = None
    similarity_score: float | None = Field(None, ge=0, le=1)
    severity_change: int | None = None
    metadata: dict[str, Any] | None = Field(default_factory=dict)


class EvolutionEntryCreate(EvolutionEntryBase):
    pass


class EvolutionEntryResponse(EvolutionEntryBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class EvolutionEntryDetailResponse(EvolutionEntryResponse):
    risk_prev: Optional["RiskItemResponse"] = None
    risk_current: Optional["RiskItemResponse"] = None


class ComparisonRequest(BaseModel):
    company_id: UUID
    year_current: int = Field(..., ge=1900, le=2100)
    year_previous: int = Field(..., ge=1900, le=2100)
    similarity_threshold: float = Field(default=0.85, ge=0, le=1)


class ComparisonResponse(BaseModel):
    company_id: UUID
    year_current: int
    year_previous: int
    new_risks: list[RiskItemResponse]
    removed_risks: list[RiskItemResponse]
    severity_increased: list[EvolutionEntryDetailResponse]
    severity_decreased: list[EvolutionEntryDetailResponse]
    modified_risks: list[EvolutionEntryDetailResponse]
    total_changes: int
    ai_summary: str | None = None
    processing_time_seconds: float


class RiskEvolutionTimeline(BaseModel):
    company_id: UUID
    risk_category: str
    timeline: list[dict[str, Any]]


class EvolutionSummary(BaseModel):
    company_id: UUID
    period: str
    total_risks_current: int
    total_risks_previous: int
    net_change: int
    new_risks_count: int
    removed_risks_count: int
    severity_changes: dict[str, int]
    top_new_categories: list[dict[str, Any]]
    top_removed_categories: list[dict[str, Any]]
    ai_narrative: str

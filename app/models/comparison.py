from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.config.constants import ChangeType
from app.models.risk import RiskEvidence, RiskItemResponse



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





class EvolutionChangeType(str, Enum):
    NEW = "NEW"
    REMOVED = "REMOVED"
    UNCHANGED = "UNCHANGED"
    MODIFIED = "MODIFIED"
    ESCALATED = "ESCALATED"
    DE_ESCALATED = "DE-ESCALATED"


class AttributeChange(BaseModel):
    before: Any | None = None
    after: Any | None = None


class RiskEvolutionRecord(BaseModel):
    """Detailed record of a risk's year-over-year evolution classification."""

    year_1_risk_id: str | None = None
    year_2_risk_id: str | None = None
    report_id_prev: str | None = None
    report_id_current: str | None = None
    report_year_prev: int | None = None
    report_year_current: int | None = None
    change_type: EvolutionChangeType
    match_confidence: float = Field(0.0, ge=0.0, le=1.0)
    semantic_similarity: float = Field(0.0, ge=0.0, le=1.0)
    severity_prev: str | None = None
    severity_current: str | None = None
    likelihood_prev: str | None = None
    likelihood_current: str | None = None
    impact_prev: str | None = None
    impact_current: str | None = None
    changed_attributes: dict[str, AttributeChange] = Field(default_factory=dict)
    evidence_prev: RiskEvidence | None = None
    evidence_current: RiskEvidence | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvolutionSummaryResult(BaseModel):
    """Structured aggregate summary of Year-over-Year risk evolution."""

    year_1: int
    year_2: int
    total_year_1_risks: int
    total_year_2_risks: int
    new_count: int = 0
    removed_count: int = 0
    unchanged_count: int = 0
    modified_count: int = 0
    escalated_count: int = 0
    de_escalated_count: int = 0
    records: list[RiskEvolutionRecord] = Field(default_factory=list)
    by_status: dict[str, list[RiskEvolutionRecord]] = Field(default_factory=dict)


class CandidateMatch(BaseModel):
    """Candidate match record between a Year-2 risk and a Year-1 risk."""

    year_1_risk_id: str
    semantic_similarity: float = Field(..., ge=0.0, le=1.0)
    match_confidence: float = Field(..., ge=0.0, le=1.0)
    category_match: bool = False
    title_similarity: float = 0.0
    matching_signals: dict[str, Any] = Field(default_factory=dict)


class RiskMatchResult(BaseModel):
    """Semantic matching result for a single Year-2 risk against Year-1 candidates."""

    year_2_risk_id: str
    candidate_matches: list[CandidateMatch] = Field(default_factory=list)
    best_match: CandidateMatch | None = None


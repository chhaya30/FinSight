from typing import Any

from pydantic import BaseModel, Field

from app.models.comparison import EvolutionChangeType, RiskEvolutionRecord


class EvidenceReference(BaseModel):
    """A traceable source reference attached to an explainability claim."""

    side: str = Field(pattern="^(year_1|year_2)$")
    document_id: str
    report_year: int | None = None
    page: int = Field(..., ge=1)
    chunk_id: str | None = None
    text_excerpt: str = ""


class ExplainabilityClaim(BaseModel):
    """A statement that cannot exist without supporting source references."""

    text: str
    evidence: list[EvidenceReference] = Field(default_factory=list)


class AttributeDifference(BaseModel):
    name: str
    before: Any | None = None
    after: Any | None = None


class ExplainableRiskEvolution(BaseModel):
    """Evidence chain and deterministic explanation for one evolution record."""

    year_1_risk_id: str | None = None
    year_2_risk_id: str | None = None
    report_id_prev: str | None = None
    report_id_current: str | None = None
    report_year_prev: int | None = None
    report_year_current: int | None = None
    change_type: EvolutionChangeType
    what_changed: list[AttributeDifference] = Field(default_factory=list)
    why_it_matters: ExplainabilityClaim
    executive_summary: ExplainabilityClaim
    business_impact: ExplainabilityClaim
    confidence_score: float = Field(..., ge=0, le=1)
    confidence_reason: str
    supporting_evidence: list[EvidenceReference] = Field(default_factory=list)
    source_record: RiskEvolutionRecord


class ExplainabilityRequest(BaseModel):
    records: list[RiskEvolutionRecord] = Field(min_length=1)


class ExplainabilityResponse(BaseModel):
    explanations: list[ExplainableRiskEvolution]
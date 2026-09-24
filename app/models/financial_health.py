from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.comparison import RiskEvolutionRecord
from app.models.explainability import EvidenceReference


class FinancialMetricValue(BaseModel):
    metric_name: str
    value: float | None = None
    unit: str = "absolute"
    report_year: int = Field(..., ge=1900, le=2100)
    document_id: str
    page: int = Field(..., ge=1)
    source_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class FinancialSnapshot(BaseModel):
    company_id: UUID | str | None = None
    report_id: str | None = None
    report_year: int = Field(..., ge=1900, le=2100)
    document_id: str
    metrics: dict[str, FinancialMetricValue] = Field(default_factory=dict)


class FinancialMetricChange(BaseModel):
    metric_name: str
    report_year_prev: int
    report_year_current: int
    previous_value: float | None = None
    current_value: float | None = None
    absolute_change: float | None = None
    percent_change: float | None = None
    direction: str = Field(pattern="^(INCREASED|DECREASED|UNCHANGED|UNAVAILABLE)$")
    supporting_evidence: list[EvidenceReference] = Field(default_factory=list)


class RiskFinancialCorrelation(BaseModel):
    risk_item_id_prev: str | None = None
    risk_item_id_current: str | None = None
    change_type: str
    metric_name: str
    metric_direction: str
    relationship: str = "ASSOCIATED_DISCLOSURE_OVERLAP"
    explanation: str
    confidence_score: float = Field(..., ge=0, le=1)
    supporting_evidence: list[EvidenceReference] = Field(default_factory=list)


class FinancialHealthAnalysis(BaseModel):
    snapshot_previous: FinancialSnapshot | None = None
    snapshot_current: FinancialSnapshot
    changes: list[FinancialMetricChange] = Field(default_factory=list)
    correlations: list[RiskFinancialCorrelation] = Field(default_factory=list)


class FinancialHealthRequest(BaseModel):
    snapshot_previous: FinancialSnapshot | None = None
    snapshot_current: FinancialSnapshot
    evolution_records: list[RiskEvolutionRecord] = Field(default_factory=list)


class FinancialHealthResponse(FinancialHealthAnalysis):
    pass
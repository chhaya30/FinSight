from uuid import UUID

from pydantic import BaseModel, Field

from app.models.comparison import EvolutionChangeType, RiskEvolutionRecord
from app.models.explainability import AttributeDifference, EvidenceReference, ExplainabilityClaim
from app.models.financial_health import (
    FinancialMetricChange,
    FinancialMetricValue,
    RiskFinancialCorrelation,
)


class DashboardCompany(BaseModel):
    id: UUID | str
    name: str
    sector: str | None = None


class DashboardReport(BaseModel):
    year: int
    report_id: str
    source_file: str


class DashboardRiskChange(BaseModel):
    year_1_risk_id: str | None = None
    year_2_risk_id: str | None = None
    title: str | None = None
    category: str | None = None
    severity_previous: str | None = None
    severity_current: str | None = None
    change_type: EvolutionChangeType
    what_changed: list[AttributeDifference] = Field(default_factory=list)
    why_it_matters: ExplainabilityClaim
    confidence: float = Field(..., ge=0, le=1)
    evidence: list[EvidenceReference] = Field(default_factory=list)


class ExecutiveDashboardResponse(BaseModel):
    company: DashboardCompany
    reports: list[DashboardReport]
    total_risks_previous: int
    total_risks_current: int
    risk_counts_by_status: dict[str, int]
    key_risk_changes: list[DashboardRiskChange]
    executive_summary: ExplainabilityClaim
    business_impact: ExplainabilityClaim
    financial_metrics: list[FinancialMetricValue] = Field(default_factory=list)
    financial_changes: list[FinancialMetricChange] = Field(default_factory=list)
    risk_financial_correlations: list[RiskFinancialCorrelation] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    source_records: list[RiskEvolutionRecord] = Field(default_factory=list)
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.explainability import ExplainableRiskEvolution
from app.models.financial_health import FinancialHealthAnalysis
from app.models.industry_intelligence import IndustryIntelligenceResponse
from app.models.market_intelligence import MarketIntelligenceResponse


class RiskExplorerItem(BaseModel):
    risk_id: UUID
    company_id: UUID
    company_name: str
    report_id: UUID
    year: int
    comparison_year: int
    category: str
    severity: str
    status: str
    title: str
    summary: str
    confidence: float = Field(ge=0, le=1)
    source_document: str
    source_page: int | None = None
    previous_risk_id: UUID | None = None


class RiskExplorerListResponse(BaseModel):
    items: list[RiskExplorerItem]
    total: int
    page: int
    page_size: int
    companies: list[dict[str, Any]]
    categories: list[str]
    severities: list[str]
    years: list[int]
    statuses: list[str]


class RiskExplorerEvidence(BaseModel):
    document: str
    source_url: str | None = None
    year: int
    page: int | None = None
    chunk_id: UUID | None = None
    source: str
    text: str


class ClassificationConfidenceDetail(BaseModel):
    category_confidence: float = Field(ge=0, le=1)
    severity_confidence: float = Field(ge=0, le=1)
    classification_confidence: float = Field(ge=0, le=1)
    evidence_quality: float = Field(ge=0, le=1)
    low_confidence: bool
    confidence_reason: str
    supporting_evidence: list[RiskExplorerEvidence] = Field(default_factory=list)


class RiskExplorerRiskVersion(BaseModel):
    risk_id: UUID
    year: int
    category: str
    severity: str
    confidence: float
    title: str
    summary: str
    evidence: RiskExplorerEvidence
    classification_assessment: ClassificationConfidenceDetail


class RiskExplorerDetailResponse(BaseModel):
    company_id: UUID
    company_name: str
    status: str
    current_risk: RiskExplorerRiskVersion | None = None
    previous_risk: RiskExplorerRiskVersion | None = None
    explanation: ExplainableRiskEvolution | None = None
    financial_analysis: FinancialHealthAnalysis | None = None
    market_signals: MarketIntelligenceResponse | None = None
    industry_signals: IndustryIntelligenceResponse | None = None

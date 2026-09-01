from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CompanyProfileBase(BaseModel):
    company_id: UUID
    business_description: str | None = None
    key_products: list[str] | None = Field(default_factory=list)
    geographic_presence: list[str] | None = Field(default_factory=list)
    major_customers: list[str] | None = Field(default_factory=list)
    competitors: list[str] | None = Field(default_factory=list)
    metadata: dict[str, Any] | None = Field(default_factory=dict)


class CompanyProfileCreate(CompanyProfileBase):
    pass


class CompanyProfileResponse(CompanyProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class FinancialMetric(BaseModel):
    metric_name: str
    value: float | None = None
    unit: str = "absolute"
    period: str
    trend: str | None = None
    change_pct: float | None = None


class FinancialHealthResponse(BaseModel):
    company_id: UUID
    fiscal_year: int
    metrics: list[FinancialMetric]
    revenue: float | None = None
    profit: float | None = None
    net_margin: float | None = None
    roe: float | None = None
    roce: float | None = None
    eps: float | None = None
    debt_equity: float | None = None
    cash_flow: float | None = None
    market_cap: float | None = None
    ai_interpretation: str | None = None
    risk_correlation: dict[str, Any] | None = None


class PeerComparisonRequest(BaseModel):
    company_id: UUID
    peer_company_ids: list[UUID] | None = None
    sector: str | None = None
    metrics: list[str] | None = None


class PeerComparisonResponse(BaseModel):
    company_id: UUID
    peers: list[dict[str, Any]]
    benchmark_metrics: dict[str, Any]
    risk_profile_comparison: dict[str, Any]
    ranking: int | None = None
    total_peers: int


class IndustryAnalysisResponse(BaseModel):
    sector: str
    total_companies: int
    risk_heatmap: dict[str, dict[str, int]]
    common_risks: list[dict[str, Any]]
    emerging_risks: list[dict[str, Any]]
    sector_benchmark: dict[str, float]
    trend_analysis: dict[str, Any]


class RiskScannerRequest(BaseModel):
    filters: dict[str, Any]
    logic: str = Field(default="AND", pattern="^(AND|OR)$")
    companies: list[UUID] | None = None
    sectors: list[str] | None = None
    years: list[int] | None = None


class RiskScannerResponse(BaseModel):
    scan_id: UUID
    filters: dict[str, Any]
    logic: str
    matched_companies: list[dict[str, Any]]
    total_matches: int
    risk_breakdown: dict[str, int]


class NewsArticle(BaseModel):
    title: str
    source: str
    url: str
    published_at: datetime
    summary: str | None = None
    sentiment: str | None = None
    relevance_score: float | None = None


class NewsAnalysisResponse(BaseModel):
    company_id: UUID
    articles: list[NewsArticle]
    sentiment_summary: dict[str, Any]
    risk_correlation: dict[str, Any]
    event_timeline: list[dict[str, Any]]


class ExecutiveSummaryRequest(BaseModel):
    company_id: UUID
    year: int | None = None
    include_evolution: bool = True
    include_financial: bool = True
    include_news: bool = True


class ExecutiveSummaryResponse(BaseModel):
    company_id: UUID
    company_name: str
    fiscal_year: int
    overall_risk_score: float
    risk_distribution: dict[str, int]
    top_risks: list[dict[str, Any]]
    key_changes: list[dict[str, Any]]
    financial_health: str | None = None
    news_highlights: list[str] | None = None
    ai_narrative: str
    confidence_score: float
    generated_at: datetime

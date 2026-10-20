from datetime import date, datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


class IndustryRiskCategory(str, Enum):
    REGULATORY = "REGULATORY"
    MARKET = "MARKET"
    CREDIT = "CREDIT"
    LIQUIDITY = "LIQUIDITY"
    OPERATIONAL = "OPERATIONAL"
    CYBER = "CYBER"
    LEGAL = "LEGAL"
    MACROECONOMIC = "MACROECONOMIC"
    GENERAL = "GENERAL"


class IndustryEvidence(BaseModel):
    source: str = Field(min_length=1)
    source_url: HttpUrl | None = None
    publication_date: date | None = None
    excerpt: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IndustryRiskTheme(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    industry: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category: IndustryRiskCategory = IndustryRiskCategory.GENERAL
    severity: str | None = None
    relevance_score: float = Field(0.0, ge=0, le=1)
    evidence: IndustryEvidence
    supporting_evidence: list[IndustryEvidence] = Field(default_factory=list)
    provider: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IndustryPeer(BaseModel):
    company_id: UUID | str
    name: str = Field(min_length=1)
    industry: str | None = None
    risk_categories: list[str] = Field(default_factory=list)
    evidence: list[IndustryEvidence] = Field(default_factory=list)


class IndustryRiskAssessment(BaseModel):
    risk_id: str
    title: str
    category: str | None = None
    severity: str | None = None
    classification: str = Field(pattern="^(INDUSTRY_WIDE|COMPANY_SPECIFIC|UNCLASSIFIED)$")
    relevance_score: float = Field(0.0, ge=0, le=1)
    supporting_themes: list[UUID] = Field(default_factory=list)
    evidence: list[IndustryEvidence] = Field(default_factory=list)
    explanation: str


class PeerRiskComparison(BaseModel):
    category: str
    company_present: bool
    peer_count: int = Field(ge=0)
    peer_names: list[str] = Field(default_factory=list)
    relevance_score: float = Field(0.0, ge=0, le=1)
    evidence: list[IndustryEvidence] = Field(default_factory=list)
    explanation: str


class IndustryIntelligenceResponse(BaseModel):
    company_id: UUID | str
    company_name: str
    industry: str | None = None
    provider: str
    provider_available: bool
    themes: list[IndustryRiskTheme] = Field(default_factory=list)
    peers: list[IndustryPeer] = Field(default_factory=list)
    assessments: list[IndustryRiskAssessment] = Field(default_factory=list)
    peer_comparisons: list[PeerRiskComparison] = Field(default_factory=list)
    error: str | None = None

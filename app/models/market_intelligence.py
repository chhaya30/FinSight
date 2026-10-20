from datetime import date, datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


class MarketRiskCategory(str, Enum):
    REGULATORY = "REGULATORY"
    MARKET = "MARKET"
    CREDIT = "CREDIT"
    LIQUIDITY = "LIQUIDITY"
    OPERATIONAL = "OPERATIONAL"
    CYBER = "CYBER"
    LEGAL = "LEGAL"
    MACROECONOMIC = "MACROECONOMIC"
    GENERAL = "GENERAL"


class MarketEvidence(BaseModel):
    source: str
    source_url: HttpUrl | None = None
    publication_date: date | None = None
    excerpt: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    company_id: UUID | str
    title: str = Field(min_length=1)
    source: str = Field(min_length=1)
    source_url: HttpUrl | None = None
    publication_date: date | None = None
    summary: str | None = None
    category: MarketRiskCategory = MarketRiskCategory.GENERAL
    relevance_score: float = Field(0.0, ge=0, le=1)
    evidence: MarketEvidence
    provider: str
    is_fallback: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RelatedRisk(BaseModel):
    event_id: UUID
    risk_item_id_prev: str | None = None
    risk_item_id_current: str | None = None
    change_type: str | None = None
    relationship: str = "SUPPORTED_TERM_OVERLAP"
    confidence_score: float = Field(0.0, ge=0, le=1)
    evidence: list[MarketEvidence] = Field(default_factory=list)
    explanation: str


class MarketIntelligenceResponse(BaseModel):
    company_id: UUID | str
    company_name: str
    provider: str
    provider_available: bool
    events: list[MarketEvent] = Field(default_factory=list)
    related_risks: list[RelatedRisk] = Field(default_factory=list)
    error: str | None = None
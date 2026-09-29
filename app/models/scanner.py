from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


ScannerFactor = Literal[
    "category", "status", "severity", "financial_signal", "market_signal", "industry_signal",
    "evidence_quality", "classification_confidence",
]


class ScannerCriterion(BaseModel):
    factor: ScannerFactor
    operator: Literal["eq", "gte", "observed"]
    value: str | float | bool | None = None

    @model_validator(mode="after")
    def validate_value(self):
        if self.operator == "observed" and not isinstance(self.value, bool):
            raise ValueError("observed criteria require a boolean value")
        if self.operator != "observed" and self.value is None:
            raise ValueError("eq and gte criteria require a value")
        return self


class ScannerRequest(BaseModel):
    company_ids: list[UUID] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    year_current: int | None = Field(None, ge=1900, le=2100)
    year_previous: int | None = Field(None, ge=1900, le=2100)
    logic: Literal["AND", "OR"] = "AND"
    criteria: list[ScannerCriterion] = Field(default_factory=list)
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=100)

    @model_validator(mode="after")
    def validate_year_pair(self):
        if self.year_previous is not None and self.year_current is None:
            raise ValueError("year_current is required when year_previous is supplied")
        if self.year_previous is not None and self.year_current is not None:
            if self.year_previous >= self.year_current:
                raise ValueError("year_previous must be earlier than year_current")
        return self


class ScannerEvidence(BaseModel):
    document_id: str | None = None
    source_url: str | None = None
    report_year: int | None = None
    page: int | None = None
    chunk_id: str | None = None
    source: str
    excerpt: str = ""


class ContributingFactor(BaseModel):
    factor: ScannerFactor
    label: str
    observed: bool
    value: Any = None
    score: float | None = Field(None, ge=0, le=1)
    explanation: str
    evidence: list[ScannerEvidence] = Field(default_factory=list)


class ScannerResult(BaseModel):
    risk_id: str
    company_id: UUID
    company_name: str
    sector: str | None = None
    report_year: int
    previous_year: int | None = None
    title: str
    category: str
    severity: str
    status: str
    classification_confidence: float = Field(ge=0, le=1)
    evidence_quality: float = Field(ge=0, le=1)
    overall_score: float = Field(ge=0, le=1)
    assessment: str
    coverage: float = Field(ge=0, le=1)
    matched: bool
    contributing_factors: list[ContributingFactor]


class ScannerResponse(BaseModel):
    scan_id: UUID = Field(default_factory=uuid4)
    logic: Literal["AND", "OR"]
    criteria: list[ScannerCriterion]
    total_matches: int
    page: int
    page_size: int
    results: list[ScannerResult]
    factor_weights: dict[str, float]


class ScannerOptionsResponse(BaseModel):
    companies: list[dict[str, Any]]
    sectors: list[str]
    years: list[int]
    categories: list[str]
    severities: list[str]
    statuses: list[str]
    factor_operators: dict[str, list[str]]

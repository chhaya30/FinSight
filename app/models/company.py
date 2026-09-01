from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CompanyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sector: str | None = Field(None, max_length=100)
    market_cap: float | None = Field(None, ge=0)
    listed_exchange: str | None = Field(None, max_length=50)
    workspace_id: UUID | None = None
    metadata: dict[str, Any] | None = Field(default_factory=dict)


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    sector: str | None = Field(None, max_length=100)
    market_cap: float | None = Field(None, ge=0)
    listed_exchange: str | None = Field(None, max_length=50)
    metadata: dict[str, Any] | None = None


class CompanyResponse(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class CompanyListResponse(BaseModel):
    companies: list[CompanyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CompanyDetailResponse(CompanyResponse):
    reports_count: int = 0
    latest_report_year: int | None = None
    risk_count: int = 0
    financial_snapshots_count: int = 0

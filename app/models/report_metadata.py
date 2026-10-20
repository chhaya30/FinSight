from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator

MARKET_ALIASES = {
    "sec": "SEC", "us sec": "SEC", "securities and exchange commission": "SEC",
    "bse": "BSE", "bombay stock exchange": "BSE",
    "nse": "NSE", "national stock exchange": "NSE",
    "bse/nse": "BSE_NSE", "bse nse": "BSE_NSE",
}
COUNTRY_ALIASES = {"us": "USA", "usa": "USA", "united states": "USA", "india": "India"}
REPORT_TYPE_ALIASES = {
    "annual report": "annual_report", "annual report filing": "annual_report",
    "annual_report": "annual_report", "10-k": "10-K", "10k": "10-K",
    "10-q": "10-Q", "10q": "10-Q", "drhp": "DRHP",
}


def _key(value: str | None) -> str | None:
    return " ".join(value.strip().lower().replace("_", " ").split()) if value else None


def normalize_market(value: str | None) -> str | None:
    key = _key(value)
    return MARKET_ALIASES.get(key, value.strip().upper() if value else None)


def normalize_country(value: str | None) -> str | None:
    key = _key(value)
    return COUNTRY_ALIASES.get(key, value.strip() if value else None)


def normalize_report_type(value: str | None) -> str:
    key = _key(value) or "annual report"
    return REPORT_TYPE_ALIASES.get(key, value.strip() if value else "annual_report")


class ReportMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    market: str | None = None
    country: str | None = None
    ticker: str | None = Field(None, max_length=32)
    exchange: str | None = Field(None, max_length=50)
    isin: str | None = Field(None, max_length=20)
    cin: str | None = Field(None, max_length=24)
    currency: str | None = Field(None, max_length=8)
    sector: str | None = Field(None, max_length=100)
    source_url: str | None = None
    reporting_period: str | None = None
    auditor_name: str | None = None
    extraction_method: str | None = None
    ocr_used: bool = False
    metadata_sources: dict[str, str] = Field(default_factory=dict)

    @field_validator("market")
    @classmethod
    def validate_market(cls, value: str | None) -> str | None:
        return normalize_market(value)

    @field_validator("country")
    @classmethod
    def validate_country(cls, value: str | None) -> str | None:
        return normalize_country(value)


def merge_report_metadata(
    *, explicit: Mapping[str, Any] | None = None,
    company: Mapping[str, Any] | None = None,
    extracted: Mapping[str, Any] | None = None,
) -> ReportMetadata:
    """Merge with precedence: API input, company record, then PDF extraction."""
    result: dict[str, Any] = {}
    sources: dict[str, str] = {}
    for source_name, values in (("pdf_extraction", extracted), ("company_database", company), ("api_input", explicit)):
        for key, value in (values or {}).items():
            if value not in (None, ""):
                result[key] = value
                sources[key] = source_name
    result["metadata_sources"] = sources
    return ReportMetadata.model_validate(result)

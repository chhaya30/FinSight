from collections.abc import Iterable
from datetime import date, datetime
from typing import Any, Protocol

from app.models.comparison import RiskEvolutionRecord
from app.models.market_intelligence import (
    MarketEvent,
    MarketEvidence,
    MarketIntelligenceResponse,
    MarketRiskCategory,
    RelatedRisk,
)


class MarketIntelligenceProvider(Protocol):
    name: str

    def is_available(self) -> bool: ...

    async def fetch_events(self, company_name: str, company_id: str) -> Iterable[Any]: ...


class NullMarketProvider:
    """Safe default until a real external provider is configured."""

    name = "unconfigured"

    def is_available(self) -> bool:
        return False

    async def fetch_events(self, company_name: str, company_id: str) -> list[Any]:
        return []


class MarketIntelligenceService:
    CATEGORY_TERMS: dict[MarketRiskCategory, tuple[str, ...]] = {
        MarketRiskCategory.REGULATORY: (
            "regulator", "regulatory", "sanction", "compliance", "sec", "sebi"
        ),
        MarketRiskCategory.MARKET: ("market", "demand", "pricing", "competition", "share price"),
        MarketRiskCategory.CREDIT: ("credit", "default", "rating", "loan"),
        MarketRiskCategory.LIQUIDITY: ("liquidity", "refinancing", "funding", "cash"),
        MarketRiskCategory.OPERATIONAL: ("outage", "supplier", "supply chain", "disruption"),
        MarketRiskCategory.CYBER: ("cyber", "breach", "ransomware", "security incident"),
        MarketRiskCategory.LEGAL: ("lawsuit", "litigation", "court", "legal"),
        MarketRiskCategory.MACROECONOMIC: (
            "inflation", "interest rate", "tariff", "recession", "gdp"
        ),
    }

    def __init__(self, provider: MarketIntelligenceProvider | None = None):
        self.provider = provider or NullMarketProvider()

    async def fetch_for_company(
        self,
        company_id: str,
        company_name: str,
        risk_records: list[RiskEvolutionRecord] | None = None,
    ) -> MarketIntelligenceResponse:
        try:
            raw_events = await self.provider.fetch_events(company_name, company_id)
            events = self.normalize_events(raw_events, company_id)
            related = self.correlate_risks(events, risk_records or [])
            return MarketIntelligenceResponse(
                company_id=company_id,
                company_name=company_name,
                provider=self.provider.name,
                provider_available=self.provider.is_available(),
                events=events,
                related_risks=related,
            )
        except Exception as exc:
            return MarketIntelligenceResponse(
                company_id=company_id,
                company_name=company_name,
                provider=self.provider.name,
                provider_available=False,
                error=f"Market provider unavailable: {type(exc).__name__}",
            )

    def normalize_events(self, raw_events: Iterable[Any], company_id: str) -> list[MarketEvent]:
        events: list[MarketEvent] = []
        for raw in raw_events or []:
            try:
                event = self._normalize_event(raw, company_id)
            except (TypeError, ValueError):
                continue
            if event is not None:
                events.append(event)
        return events

    def correlate_risks(
        self,
        events: list[MarketEvent],
        risk_records: list[RiskEvolutionRecord],
    ) -> list[RelatedRisk]:
        related: list[RelatedRisk] = []
        for event in events:
            event_terms = self._terms(f"{event.title} {event.summary or ''}")
            for record in risk_records:
                risk_terms = self._terms(self._risk_text(record))
                overlap = sorted(event_terms & risk_terms)
                if not overlap:
                    continue
                confidence = round(min(1.0, 0.5 + 0.1 * len(overlap)), 4)
                related.append(
                    RelatedRisk(
                        event_id=event.id,
                        risk_item_id_prev=record.year_1_risk_id,
                        risk_item_id_current=record.year_2_risk_id,
                        change_type=record.change_type.value,
                        confidence_score=confidence,
                        evidence=[event.evidence],
                        explanation=(
                            "Event and risk disclosures share supported terms: "
                            f"{', '.join(overlap)}. "
                            "This indicates relevance, not causation."
                        ),
                    )
                )
        return related

    def classify_category(self, text: str) -> MarketRiskCategory:
        terms = self._terms(text)
        for category, category_terms in self.CATEGORY_TERMS.items():
            if terms.intersection(self._terms(" ".join(category_terms))):
                return category
        return MarketRiskCategory.GENERAL

    def calculate_relevance(self, title: str, summary: str | None, company_name: str) -> float:
        text = f"{title} {summary or ''}".lower()
        score = 0.2
        if company_name.lower() in text:
            score += 0.4
        if any(term in text for terms in self.CATEGORY_TERMS.values() for term in terms):
            score += 0.3
        if summary:
            score += min(0.1, len(summary.strip()) / 1000)
        return round(min(score, 1.0), 4)

    def _normalize_event(self, raw: Any, company_id: str) -> MarketEvent | None:
        if isinstance(raw, MarketEvent):
            return raw.model_copy(update={"company_id": company_id})
        if not isinstance(raw, dict):
            return None
        title = raw.get("title") or raw.get("event_title")
        source = raw.get("source") or raw.get("publisher")
        if (
            not isinstance(title, str)
            or not title.strip()
            or not isinstance(source, str)
            or not source.strip()
        ):
            return None
        publication_date = self._date(raw.get("publication_date") or raw.get("published_at"))
        summary = raw.get("summary")
        if summary is not None and not isinstance(summary, str):
            summary = None
        category = self.classify_category(f"{title} {summary or ''}")
        relevance = raw.get("relevance_score")
        if not isinstance(relevance, (int, float)) or not 0 <= relevance <= 1:
            relevance = self.calculate_relevance(title, summary, raw.get("company_name", ""))
        source_url = raw.get("source_url") or raw.get("url")
        evidence = MarketEvidence(
            source=source,
            source_url=source_url,
            publication_date=publication_date,
            excerpt=raw.get("excerpt") or summary,
            metadata=raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {},
        )
        return MarketEvent(
            company_id=company_id,
            title=title.strip(),
            source=source.strip(),
            source_url=source_url,
            publication_date=publication_date,
            summary=summary,
            category=category,
            relevance_score=float(relevance),
            evidence=evidence,
            provider=raw.get("provider", self.provider.name),
            is_fallback=bool(raw.get("is_fallback", False)),
        )

    @staticmethod
    def _date(value: Any) -> date | None:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
            except ValueError:
                return None
        return None

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {term for term in text.lower().replace("-", " ").split() if len(term) > 3}

    @staticmethod
    def _risk_text(record: RiskEvolutionRecord) -> str:
        return " ".join(str(value) for value in record.metadata.values())

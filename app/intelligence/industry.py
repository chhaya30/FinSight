from datetime import date, datetime
from typing import Any, Protocol

from app.models.comparison import RiskEvolutionRecord
from app.models.industry_intelligence import (
    IndustryEvidence,
    IndustryIntelligenceResponse,
    IndustryPeer,
    IndustryRiskAssessment,
    IndustryRiskCategory,
    IndustryRiskTheme,
    PeerRiskComparison,
)


class IndustryIntelligenceProvider(Protocol):
    name: str

    def is_available(self) -> bool: ...

    async def fetch_industry_data(self, company_name: str, industry: str) -> dict[str, Any]: ...


class NullIndustryProvider:
    """Safe default until a real sector or peer provider is configured."""

    name = "unconfigured"

    def is_available(self) -> bool:
        return False

    async def fetch_industry_data(self, company_name: str, industry: str) -> dict[str, Any]:
        return {}


class IndustryIntelligenceService:
    CATEGORY_TERMS: dict[IndustryRiskCategory, tuple[str, ...]] = {
        IndustryRiskCategory.REGULATORY: ("regulatory", "regulator", "compliance", "sec", "sebi"),
        IndustryRiskCategory.MARKET: ("market", "demand", "pricing", "competition"),
        IndustryRiskCategory.CREDIT: ("credit", "default", "rating", "loan"),
        IndustryRiskCategory.LIQUIDITY: ("liquidity", "refinancing", "funding", "cash"),
        IndustryRiskCategory.OPERATIONAL: ("outage", "supplier", "supply chain", "disruption"),
        IndustryRiskCategory.CYBER: ("cyber", "cybersecurity", "breach", "ransomware", "security"),
        IndustryRiskCategory.LEGAL: ("lawsuit", "litigation", "court", "legal"),
        IndustryRiskCategory.MACROECONOMIC: ("inflation", "interest rate", "tariff", "recession"),
    }

    def __init__(self, provider: IndustryIntelligenceProvider | None = None):
        self.provider = provider or NullIndustryProvider()

    async def analyze_company(
        self,
        company_id: str,
        company_name: str,
        industry: str | None,
        risk_records: list[RiskEvolutionRecord] | None = None,
    ) -> IndustryIntelligenceResponse:
        if not industry:
            return self._empty(company_id, company_name, None, "Company industry is unavailable")
        try:
            raw = await self.provider.fetch_industry_data(company_name, industry)
            normalized = self.normalize_data(raw, company_id, industry)
            assessments = self.assess_risks(risk_records or [], normalized["themes"])
            comparisons = self.compare_peers(risk_records or [], normalized["peers"])
            return IndustryIntelligenceResponse(
                company_id=company_id,
                company_name=company_name,
                industry=industry,
                provider=self.provider.name,
                provider_available=self.provider.is_available(),
                themes=normalized["themes"],
                peers=normalized["peers"],
                assessments=assessments,
                peer_comparisons=comparisons,
            )
        except Exception as exc:
            return self._empty(
                company_id,
                company_name,
                industry,
                f"Industry provider unavailable: {type(exc).__name__}",
                self.provider.name,
            )

    def normalize_data(
        self, raw: dict[str, Any], company_id: str, industry: str
    ) -> dict[str, list[Any]]:
        themes = [theme for item in raw.get("themes", []) if (theme := self._theme(item, industry))]
        peers = [peer for item in raw.get("peers", []) if (peer := self._peer(item))]
        return {"themes": themes, "peers": peers}

    def assess_risks(
        self,
        risk_records: list[RiskEvolutionRecord],
        themes: list[IndustryRiskTheme],
    ) -> list[IndustryRiskAssessment]:
        assessments = []
        for record in risk_records:
            text = self._risk_text(record)
            risk_category = str(record.metadata.get("category", "")).lower()
            overlaps = [
                theme
                for theme in themes
                if self._overlap(text, theme.name)
                and (
                    not risk_category
                    or self.classify_category(risk_category) == theme.category
                )
            ]
            if overlaps:
                classification = "INDUSTRY_WIDE"
                explanation = (
                    "The risk overlaps externally sourced industry themes; "
                    "this is not a causal conclusion."
                )
                relevance = self.relevance_score(text, overlaps[0].name)
                evidence = [
                    item for theme in overlaps
                    for item in [theme.evidence, *theme.supporting_evidence]
                ]
            else:
                classification = "COMPANY_SPECIFIC" if themes else "UNCLASSIFIED"
                explanation = (
                    "No externally sourced industry theme supports an industry-wide classification."
                )
                relevance = 0.0
                evidence = []
            assessments.append(
                IndustryRiskAssessment(
                    risk_id=record.year_2_risk_id or record.year_1_risk_id or "unknown",
                    title=text[:160] or "Untitled risk",
                    category=record.metadata.get("category"),
                    severity=record.severity_current or record.severity_prev,
                    classification=classification,
                    relevance_score=relevance,
                    supporting_themes=[theme.id for theme in overlaps],
                    evidence=evidence,
                    explanation=explanation,
                )
            )
        return assessments

    def compare_peers(
        self,
        risk_records: list[RiskEvolutionRecord],
        peers: list[IndustryPeer],
    ) -> list[PeerRiskComparison]:
        company_categories = {
            str(record.metadata.get("category", "")).upper() for record in risk_records
        }
        peer_categories = sorted(
            {category.upper() for peer in peers for category in peer.risk_categories}
        )
        comparisons = []
        for category in peer_categories:
            names = [
                peer.name
                for peer in peers
                if category in {item.upper() for item in peer.risk_categories}
            ]
            present = category in company_categories
            comparisons.append(
                PeerRiskComparison(
                    category=category,
                    company_present=present,
                    peer_count=len(names),
                    peer_names=names,
                    relevance_score=1.0 if present else 0.5,
                    evidence=[
                        evidence
                        for peer in peers
                        if peer.name in names
                        for evidence in peer.evidence
                    ],
                    explanation=(
                        "Category is shared with sourced peer data; no causation is inferred."
                    ),
                )
            )
        return comparisons

    def classify_category(self, text: str) -> IndustryRiskCategory:
        normalized = self._terms(text)
        for category, terms in self.CATEGORY_TERMS.items():
            if normalized.intersection(self._terms(" ".join(terms))):
                return category
        return IndustryRiskCategory.GENERAL

    @staticmethod
    def relevance_score(risk_text: str, theme_text: str) -> float:
        risk_terms = IndustryIntelligenceService._terms(risk_text)
        theme_terms = IndustryIntelligenceService._terms(theme_text)
        if not risk_terms or not theme_terms:
            return 0.0
        return round(len(risk_terms & theme_terms) / len(risk_terms | theme_terms), 4)

    def _theme(self, raw: Any, industry: str) -> IndustryRiskTheme | None:
        if (
            not isinstance(raw, dict)
            or not isinstance(raw.get("name"), str)
            or not isinstance(raw.get("source"), str)
        ):
            return None
        evidence = self._evidence(raw)
        if evidence is None:
            return None
        return IndustryRiskTheme(
            industry=industry,
            name=raw["name"].strip(),
            category=self.classify_category(f"{raw['name']} {raw.get('category', '')}"),
            severity=raw.get("severity") if isinstance(raw.get("severity"), str) else None,
            relevance_score=self._score(raw.get("relevance_score")),
            evidence=evidence,
            supporting_evidence=[
                parsed for value in raw.get("supporting_evidence", [])
                if isinstance(value, dict) and (parsed := self._evidence(value))
            ],
            provider=raw.get("provider", self.provider.name),
        )

    def _peer(self, raw: Any) -> IndustryPeer | None:
        if (
            not isinstance(raw, dict)
            or not isinstance(raw.get("name"), str)
            or not raw.get("company_id")
        ):
            return None
        evidence = [item for value in raw.get("evidence", []) if (item := self._evidence(value))]
        return IndustryPeer(
            company_id=str(raw["company_id"]),
            name=raw["name"],
            industry=raw.get("industry"),
            risk_categories=[
                value for value in raw.get("risk_categories", []) if isinstance(value, str)
            ],
            evidence=evidence,
        )

    @staticmethod
    def _evidence(raw: dict[str, Any]) -> IndustryEvidence | None:
        source = raw.get("source")
        if not isinstance(source, str) or not source.strip():
            return None
        publication_date = raw.get("publication_date")
        if isinstance(publication_date, str):
            try:
                publication_date = datetime.fromisoformat(
                    publication_date.replace("Z", "+00:00")
                ).date()
            except ValueError:
                publication_date = None
        if publication_date is not None and not isinstance(publication_date, date):
            publication_date = None
        return IndustryEvidence(
            source=source,
            source_url=raw.get("source_url"),
            publication_date=publication_date,
            excerpt=raw.get("excerpt"),
            metadata=raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {},
        )

    @staticmethod
    def _risk_text(record: RiskEvolutionRecord) -> str:
        return " ".join(str(value) for value in record.metadata.values())

    @staticmethod
    def _score(value: Any) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            return 0.0
        return score if 0 <= score <= 1 else 0.0

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {term for term in text.lower().replace("-", " ").split() if len(term) > 3}

    @classmethod
    def _overlap(cls, left: str, right: str) -> bool:
        return bool(cls._terms(left) & cls._terms(right))

    @staticmethod
    def _empty(
        company_id: str, company_name: str, industry: str | None, error: str,
        provider: str = "unconfigured",
    ):
        return IndustryIntelligenceResponse(
            company_id=company_id,
            company_name=company_name,
            industry=industry,
            provider=provider,
            provider_available=False,
            error=error,
        )

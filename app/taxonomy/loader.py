import json
from pathlib import Path
from typing import Any

from app.config.logging import get_logger
from app.config.settings import get_settings

logger = get_logger(__name__)


class RiskTaxonomy:
    def __init__(self, data: dict[str, Any]):
        self.version = data.get("version", "1.0")
        self.categories = data.get("categories", {})
        self.severity_levels = data.get("severity_levels", {})
        self.keywords = data.get("keywords", {})
        self.subcategories = data.get("subcategories", {})

    def get_category(self, category_id: str) -> dict[str, Any] | None:
        return self.categories.get(category_id)

    def get_all_categories(self) -> list[dict[str, Any]]:
        return list(self.categories.values())

    def get_category_keywords(self, category_id: str) -> list[str]:
        return self.keywords.get(category_id, [])

    def get_severity_level(self, severity: str) -> dict[str, Any] | None:
        return self.severity_levels.get(severity)

    def get_subcategories(self, category_id: str) -> list[dict[str, Any]]:
        return self.subcategories.get(category_id, [])

    def match_category(self, text: str, threshold: int = 2) -> list[str]:
        text_lower = text.lower()
        matches = []

        for category_id, keywords in self.keywords.items():
            count = sum(1 for kw in keywords if kw.lower() in text_lower)
            if count >= threshold:
                matches.append(category_id)

        return matches

    def get_severity_weight(self, severity: str) -> int:
        level = self.get_severity_level(severity)
        return level.get("weight", 0) if level else 0


class TaxonomyLoader:
    def __init__(self, taxonomy_path: str | None = None):
        self.taxonomy_path = taxonomy_path or get_settings().RISK_TAXONOMY_PATH
        self._taxonomy: RiskTaxonomy | None = None

    def load(self) -> RiskTaxonomy:
        if self._taxonomy is not None:
            return self._taxonomy

        path = Path(self.taxonomy_path)
        if not path.exists():
            logger.warning("taxonomy_file_not_found", path=str(path))
            self._taxonomy = self._create_default_taxonomy()
            return self._taxonomy

        try:
            with open(path) as f:
                data = json.load(f)
            self._taxonomy = RiskTaxonomy(data)
            logger.info(
                "taxonomy_loaded",
                version=self._taxonomy.version,
                categories=len(self._taxonomy.categories),
            )
            return self._taxonomy
        except Exception as e:
            logger.error("taxonomy_load_failed", error=str(e))
            self._taxonomy = self._create_default_taxonomy()
            return self._taxonomy

    def reload(self) -> RiskTaxonomy:
        self._taxonomy = None
        return self.load()

    def _create_default_taxonomy(self) -> RiskTaxonomy:
        default_data = {
            "version": "1.0",
            "categories": {
                "operational": {
                    "name": "Operational Risk",
                    "description": "Risks from business operations and processes",
                },
                "financial": {
                    "name": "Financial Risk",
                    "description": "Risks affecting financial performance",
                },
                "regulatory": {
                    "name": "Regulatory Risk",
                    "description": "Risks from regulatory changes and compliance",
                },
                "strategic": {
                    "name": "Strategic Risk",
                    "description": "Risks to business strategy and competitiveness",
                },
                "cyber": {
                    "name": "Cyber Risk",
                    "description": "Cybersecurity and data privacy risks",
                },
                "climate": {
                    "name": "Climate Risk",
                    "description": "Physical and transition climate risks",
                },
                "governance": {
                    "name": "Governance Risk",
                    "description": "Corporate governance and board risks",
                },
                "supply_chain": {
                    "name": "Supply Chain Risk",
                    "description": "Vendor and supply chain disruptions",
                },
                "legal": {"name": "Legal Risk", "description": "Litigation and legal proceedings"},
                "reputational": {
                    "name": "Reputational Risk",
                    "description": "Brand and reputation risks",
                },
                "talent": {
                    "name": "Talent Risk",
                    "description": "Human capital and key personnel risks",
                },
                "technology": {
                    "name": "Technology Risk",
                    "description": "Technology disruption and technical debt",
                },
                "market": {"name": "Market Risk", "description": "Market and demand risks"},
                "liquidity": {
                    "name": "Liquidity Risk",
                    "description": "Cash flow and funding risks",
                },
                "credit": {"name": "Credit Risk", "description": "Counterparty and credit risks"},
                "esg": {
                    "name": "ESG Risk",
                    "description": "Environmental, social, governance risks",
                },
                "geopolitical": {
                    "name": "Geopolitical Risk",
                    "description": "Political and trade risks",
                },
                "auditor_concern": {
                    "name": "Auditor Concern",
                    "description": "Audit opinions and control weaknesses",
                },
            },
            "severity_levels": {
                "critical": {"weight": 5, "description": "Existential threat to the business"},
                "high": {
                    "weight": 4,
                    "description": "Significant impact on financials or operations",
                },
                "medium": {"weight": 3, "description": "Moderate impact, manageable with controls"},
                "low": {"weight": 2, "description": "Minor impact, routine monitoring sufficient"},
                "informational": {
                    "weight": 1,
                    "description": "Disclosed for transparency, no immediate action",
                },
            },
            "keywords": {
                "operational": [
                    "operational risk",
                    "business disruption",
                    "process failure",
                    "system outage",
                    "business continuity",
                    "disaster recovery",
                ],
                "financial": [
                    "financial risk",
                    "revenue decline",
                    "profitability",
                    "margin pressure",
                    "cost increase",
                    "earnings volatility",
                ],
                "regulatory": [
                    "regulatory risk",
                    "compliance",
                    "regulation",
                    "regulatory change",
                    "statutory",
                    "licensing",
                ],
                "strategic": [
                    "strategic risk",
                    "competition",
                    "market share",
                    "strategic initiative",
                    "business model",
                    "digital transformation",
                ],
                "cyber": [
                    "cyber",
                    "cybersecurity",
                    "data breach",
                    "information security",
                    "ransomware",
                    "phishing",
                    "data privacy",
                ],
                "climate": [
                    "climate",
                    "environmental",
                    "carbon",
                    "emission",
                    "sustainability",
                    "net zero",
                    "transition risk",
                ],
                "governance": [
                    "governance",
                    "board",
                    "corporate governance",
                    "executive compensation",
                    "succession",
                    "audit committee",
                ],
                "supply_chain": [
                    "supply chain",
                    "vendor",
                    "supplier",
                    "procurement",
                    "logistics",
                    "third party",
                    "concentration risk",
                ],
                "legal": [
                    "litigation",
                    "lawsuit",
                    "legal proceeding",
                    "contingent liability",
                    "arbitration",
                    "class action",
                ],
                "reputational": [
                    "reputation",
                    "brand",
                    "public perception",
                    "media",
                    "social media",
                    "stakeholder trust",
                ],
                "talent": [
                    "talent",
                    "human capital",
                    "key personnel",
                    "retention",
                    "recruitment",
                    "succession planning",
                ],
                "technology": [
                    "technology risk",
                    "digital",
                    "automation",
                    "AI",
                    "artificial intelligence",
                    "legacy system",
                    "technical debt",
                ],
                "market": [
                    "market risk",
                    "demand",
                    "customer",
                    "pricing",
                    "foreign exchange",
                    "commodity price",
                    "interest rate",
                ],
                "liquidity": [
                    "liquidity",
                    "cash flow",
                    "working capital",
                    "funding",
                    "solvency",
                    "debt maturity",
                    "covenant",
                ],
                "credit": [
                    "credit risk",
                    "counterparty",
                    "default",
                    "credit rating",
                    "receivables",
                    "bad debt",
                    "impairment",
                ],
                "esg": [
                    "ESG",
                    "environmental social governance",
                    "sustainability",
                    "diversity",
                    "inclusion",
                    "human rights",
                ],
                "geopolitical": [
                    "geopolitical",
                    "political risk",
                    "trade",
                    "sanctions",
                    "tariff",
                    "war",
                    "conflict",
                ],
                "auditor_concern": [
                    "auditor",
                    "audit opinion",
                    "going concern",
                    "material weakness",
                    "internal control",
                    "significant deficiency",
                ],
            },
            "subcategories": {
                "operational": [
                    {"id": "business_continuity", "name": "Business Continuity"},
                    {"id": "process_failure", "name": "Process Failure"},
                    {"id": "system_outage", "name": "System Outage"},
                ],
                "financial": [
                    {"id": "revenue_decline", "name": "Revenue Decline"},
                    {"id": "margin_pressure", "name": "Margin Pressure"},
                    {"id": "cost_overrun", "name": "Cost Overrun"},
                ],
                "cyber": [
                    {"id": "data_breach", "name": "Data Breach"},
                    {"id": "ransomware", "name": "Ransomware"},
                    {"id": "privacy_violation", "name": "Privacy Violation"},
                ],
            },
        }
        return RiskTaxonomy(default_data)


_taxonomy_loader = TaxonomyLoader()


def get_taxonomy() -> RiskTaxonomy:
    return _taxonomy_loader.load()


def reload_taxonomy() -> RiskTaxonomy:
    return _taxonomy_loader.reload()

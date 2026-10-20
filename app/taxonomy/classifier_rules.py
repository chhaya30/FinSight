from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class ClassificationRule:
    category: str
    condition: Callable[[str], bool]
    weight: float = 1.0
    description: str = ""


class RuleBasedClassifier:
    def __init__(self):
        self.rules: dict[str, list[ClassificationRule]] = {}
        self._init_default_rules()

    def _init_default_rules(self):
        self.rules = {
            "operational": [
                ClassificationRule(
                    "operational",
                    lambda t: any(
                        kw in t.lower()
                        for kw in [
                            "business disruption",
                            "process failure",
                            "system outage",
                            "operational efficiency",
                            "business continuity",
                            "disaster recovery",
                            "supply chain disruption",
                            "factory",
                            "plant",
                            "production halt",
                        ]
                    ),
                    weight=1.5,
                    description="Direct operational disruption keywords",
                ),
            ],
            "financial": [
                ClassificationRule(
                    "financial",
                    lambda t: any(
                        kw in t.lower()
                        for kw in [
                            "revenue decline",
                            "profitability",
                            "margin pressure",
                            "cost increase",
                            "earnings volatility",
                            "financial performance",
                            "impairment",
                            "write-down",
                            "goodwill",
                        ]
                    ),
                    weight=1.5,
                    description="Financial performance impact keywords",
                ),
            ],
            "regulatory": [
                ClassificationRule(
                    "regulatory",
                    lambda t: any(
                        kw in t.lower()
                        for kw in [
                            "regulatory change",
                            "compliance",
                            "new regulation",
                            "statutory requirement",
                            "license",
                            "permit",
                            "regulatory approval",
                            "sebi",
                            "sec",
                            "rbi",
                        ]
                    ),
                    weight=1.5,
                    description="Regulatory and compliance keywords",
                ),
            ],
            "strategic": [
                ClassificationRule(
                    "strategic",
                    lambda t: any(
                        kw in t.lower()
                        for kw in [
                            "competition",
                            "market share",
                            "strategic initiative",
                            "business model",
                            "digital transformation",
                            "innovation",
                            "new entrant",
                            "disruptive technology",
                        ]
                    ),
                    weight=1.3,
                    description="Strategic and competitive keywords",
                ),
            ],
            "cyber": [
                ClassificationRule(
                    "cyber",
                    lambda t: any(
                        kw in t.lower()
                        for kw in [
                            "cyber",
                            "data breach",
                            "cybersecurity",
                            "information security",
                            "ransomware",
                            "phishing",
                            "malware",
                            "hacking",
                            "data privacy",
                            "gdpr",
                            "data protection",
                        ]
                    ),
                    weight=2.0,
                    description="Cybersecurity specific keywords",
                ),
            ],
            "climate": [
                ClassificationRule(
                    "climate",
                    lambda t: any(
                        kw in t.lower()
                        for kw in [
                            "climate change",
                            "carbon emission",
                            "net zero",
                            "physical risk",
                            "transition risk",
                            "sustainability",
                            "environmental regulation",
                            "greenhouse gas",
                        ]
                    ),
                    weight=1.5,
                    description="Climate and environmental keywords",
                ),
            ],
            "governance": [
                ClassificationRule(
                    "governance",
                    lambda t: any(
                        kw in t.lower()
                        for kw in [
                            "board",
                            "corporate governance",
                            "executive compensation",
                            "succession planning",
                            "independent director",
                            "audit committee",
                            "related party transaction",
                            "whistleblower",
                        ]
                    ),
                    weight=1.3,
                    description="Governance and board keywords",
                ),
            ],
            "supply_chain": [
                ClassificationRule(
                    "supply_chain",
                    lambda t: any(
                        kw in t.lower()
                        for kw in [
                            "supply chain",
                            "vendor",
                            "supplier",
                            "procurement",
                            "single source",
                            "concentration risk",
                            "third party",
                            "logistics",
                            "raw material shortage",
                        ]
                    ),
                    weight=1.5,
                    description="Supply chain and vendor keywords",
                ),
            ],
            "legal": [
                ClassificationRule(
                    "legal",
                    lambda t: any(
                        kw in t.lower()
                        for kw in [
                            "litigation",
                            "lawsuit",
                            "legal proceeding",
                            "contingent liability",
                            "arbitration",
                            "settlement",
                            "class action",
                            "regulatory action",
                            "court order",
                            "injunction",
                        ]
                    ),
                    weight=1.8,
                    description="Legal proceedings keywords",
                ),
            ],
            "reputational": [
                ClassificationRule(
                    "reputational",
                    lambda t: any(
                        kw in t.lower()
                        for kw in [
                            "reputation",
                            "brand damage",
                            "public perception",
                            "media scrutiny",
                            "social media",
                            "stakeholder trust",
                            "customer confidence",
                            "boycott",
                        ]
                    ),
                    weight=1.3,
                    description="Reputational keywords",
                ),
            ],
            "talent": [
                ClassificationRule(
                    "talent",
                    lambda t: any(
                        kw in t.lower()
                        for kw in [
                            "key personnel",
                            "retention",
                            "recruitment",
                            "succession planning",
                            "skills gap",
                            "talent shortage",
                            "executive departure",
                            "leadership change",
                        ]
                    ),
                    weight=1.3,
                    description="Talent and HR keywords",
                ),
            ],
            "technology": [
                ClassificationRule(
                    "technology",
                    lambda t: any(
                        kw in t.lower()
                        for kw in [
                            "technology risk",
                            "legacy system",
                            "technical debt",
                            "digital transformation",
                            "automation",
                            "artificial intelligence",
                            "ai regulation",
                            "platform migration",
                            "system replacement",
                        ]
                    ),
                    weight=1.3,
                    description="Technology and digital keywords",
                ),
            ],
            "market": [
                ClassificationRule(
                    "market",
                    lambda t: any(
                        kw in t.lower()
                        for kw in [
                            "market risk",
                            "demand decline",
                            "pricing pressure",
                            "foreign exchange",
                            "commodity price",
                            "interest rate risk",
                            "equity price",
                            "customer concentration",
                        ]
                    ),
                    weight=1.3,
                    description="Market risk keywords",
                ),
            ],
            "liquidity": [
                ClassificationRule(
                    "liquidity",
                    lambda t: any(
                        kw in t.lower()
                        for kw in [
                            "liquidity risk",
                            "cash flow",
                            "working capital",
                            "funding risk",
                            "solvency",
                            "debt maturity",
                            "refinancing risk",
                            "covenant breach",
                        ]
                    ),
                    weight=1.8,
                    description="Liquidity and funding keywords",
                ),
            ],
            "credit": [
                ClassificationRule(
                    "credit",
                    lambda t: any(
                        kw in t.lower()
                        for kw in [
                            "credit risk",
                            "counterparty risk",
                            "default risk",
                            "credit rating",
                            "bad debt",
                            "provision for doubtful",
                            "impairment loss",
                            "receivables",
                        ]
                    ),
                    weight=1.5,
                    description="Credit risk keywords",
                ),
            ],
            "esg": [
                ClassificationRule(
                    "esg",
                    lambda t: any(
                        kw in t.lower()
                        for kw in [
                            "esg",
                            "environmental social",
                            "diversity inclusion",
                            "human rights",
                            "community impact",
                            "stakeholder engagement",
                            "sustainable finance",
                            "green bond",
                        ]
                    ),
                    weight=1.3,
                    description="ESG keywords",
                ),
            ],
            "geopolitical": [
                ClassificationRule(
                    "geopolitical",
                    lambda t: any(
                        kw in t.lower()
                        for kw in [
                            "geopolitical",
                            "political risk",
                            "trade war",
                            "sanctions",
                            "tariff",
                            "export control",
                            "war",
                            "conflict",
                            "regime change",
                            "political instability",
                        ]
                    ),
                    weight=1.5,
                    description="Geopolitical keywords",
                ),
            ],
            "auditor_concern": [
                ClassificationRule(
                    "auditor_concern",
                    lambda t: any(
                        kw in t.lower()
                        for kw in [
                            "auditor",
                            "audit opinion",
                            "going concern",
                            "material weakness",
                            "internal control",
                            "significant deficiency",
                            "emphasis of matter",
                            "qualified opinion",
                            "adverse opinion",
                        ]
                    ),
                    weight=2.0,
                    description="Auditor language keywords",
                ),
            ],
        }

    def add_rule(self, category: str, rule: ClassificationRule):
        if category not in self.rules:
            self.rules[category] = []
        self.rules[category].append(rule)

    def classify(self, text: str) -> dict[str, float]:
        scores = {}

        for category, rules in self.rules.items():
            total_score = 0.0
            for rule in rules:
                if rule.condition(text):
                    total_score += rule.weight
            if total_score > 0:
                scores[category] = total_score

        return scores

    def get_top_categories(self, text: str, top_k: int = 3) -> list[dict[str, Any]]:
        scores = self.classify(text)
        sorted_categories = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [{"category": cat, "score": score} for cat, score in sorted_categories[:top_k]]


CATEGORY_SEVERITY_KEYWORDS = {
    "critical": {
        "general": [
            "catastrophic",
            "existential",
            "bankruptcy",
            "going concern",
            "survival",
            "cease operations",
            "insolvency",
        ],
        "cyber": [
            "catastrophic",
            "existential",
            "ransomware",
            "data breach",
            "critical vulnerability",
            "zero-day",
            "system compromise",
            "total outage",
        ],
        "financial": [
            "material adverse effect",
            "going concern",
            "bankruptcy",
            "insolvency",
            "liquidity crisis",
            "default",
            "covenant breach",
            "significant deficiency",
        ],
        "regulatory": [
            "regulatory breach",
            "license revocation",
            "enforcement action",
            "criminal investigation",
            "material non-compliance",
        ],
        "legal": [
            "major litigation",
            "class action",
            "significant judgment",
            "injunction",
            "regulatory fine",
            "criminal liability",
        ],
        "operational": [
            "business disruption",
            "complete shutdown",
            "plant closure",
            "supply chain collapse",
        ],
        "auditor_concern": [
            "material weakness",
            "adverse opinion",
            "qualified opinion",
            "going concern",
            "significant deficiency",
        ],
    },
    "high": {
        "general": [
            "significant",
            "substantial",
            "major",
            "severe",
            "critical impact",
            "adverse effect",
            "significant adverse",
            "substantial impact",
            "major risk",
            "high probability",
        ],
        "cyber": [
            "privacy violation",
            "unauthorized access",
            "malware",
            "phishing campaign",
            "security incident",
            "vulnerability exploit",
        ],
        "financial": [
            "margin pressure",
            "revenue decline",
            "earnings volatility",
            "impairment",
            "write-down",
            "goodwill impairment",
            "credit rating downgrade",
        ],
        "regulatory": [
            "new regulation",
            "compliance cost",
            "regulatory change",
            "statutory requirement",
            "license renewal risk",
        ],
        "legal": [
            "litigation",
            "lawsuit",
            "legal proceeding",
            "contingent liability",
            "arbitration",
            "settlement",
        ],
        "operational": [
            "process failure",
            "system outage",
            "business continuity",
            "disaster recovery",
            "key supplier failure",
        ],
        "strategic": [
            "competitive threat",
            "market share loss",
            "disruptive technology",
            "business model risk",
        ],
        "reputational": [
            "reputation damage",
            "brand damage",
            "media scrutiny",
            "public backlash",
            "customer confidence loss",
        ],
    },
    "medium": {
        "general": [
            "moderate",
            "potential",
            "possible",
            "may impact",
            "could affect",
            "reasonably possible",
            "likely",
            "expected to",
            "uncertainty",
            "dependency",
        ],
        "cyber": [
            "security risk",
            "it risk",
            "technology risk",
            "privacy concern",
            "compliance gap",
        ],
        "financial": [
            "cost increase",
            "pricing pressure",
            "foreign exchange",
            "interest rate risk",
            "commodity price risk",
        ],
        "regulatory": [
            "regulatory uncertainty",
            "pending regulation",
            "compliance burden",
            "reporting requirement",
        ],
        "legal": [
            "legal uncertainty",
            "potential claim",
            "regulatory inquiry",
            "contract dispute",
        ],
        "operational": [
            "efficiency risk",
            "capacity constraint",
            "vendor risk",
            "process improvement",
        ],
        "supply_chain": [
            "single source",
            "concentration risk",
            "vendor dependency",
            "logistics disruption",
        ],
    },
    "low": {
        "general": [
            "limited",
            "minor",
            "minimal",
            "unlikely",
            "remote",
            "low probability",
            "immaterial",
            "negligible",
            "manageable",
        ],
        "cyber": [
            "low severity vulnerability",
            "minor configuration issue",
            "routine patch",
        ],
        "financial": [
            "minor cost",
            "small variance",
            "immaterial impact",
            "routine expense",
        ],
        "regulatory": [
            "routine filing",
            "minor disclosure",
            "administrative requirement",
        ],
        "legal": [
            "routine matter",
            "minor dispute",
            "standard contract",
        ],
        "operational": [
            "routine maintenance",
            "minor process issue",
            "standard operating risk",
        ],
    },
    "informational": {
        "general": [
            "disclosed for transparency",
            "no impact",
            "routine",
            "for information",
            "no material effect",
            "no expected impact",
        ],
    },
}


def _get_general_keywords() -> dict[str, list[str]]:
    """Extract general keywords from category-aware structure."""
    result = {}
    for severity, cat_dict in CATEGORY_SEVERITY_KEYWORDS.items():
        result[severity] = cat_dict.get("general", [])
    return result


class SeverityRules:
    SEVERITY_KEYWORDS = _get_general_keywords()

    @classmethod
    def classify_severity(cls, text: str, category: str = None) -> str:
        text_lower = text.lower()
        scores = {}

        for severity, keywords in cls.SEVERITY_KEYWORDS.items():
            scores[severity] = sum(2 if kw in text_lower else 0 for kw in keywords)

        if category:
            for severity in ["critical", "high", "medium", "low", "informational"]:
                cat_keywords = CATEGORY_SEVERITY_KEYWORDS.get(severity, {}).get(category, [])
                if cat_keywords:
                    scores[severity] = scores.get(severity, 0) + sum(
                        2 if kw in text_lower else 0 for kw in cat_keywords
                    )

        if not any(scores.values()):
            return "medium"

        return max(scores, key=scores.get)

    @classmethod
    def get_severity_score(cls, severity: str) -> int:
        """Convert severity level to 0-10 score."""
        severity_scores = {
            "informational": 1,
            "low": 3,
            "medium": 5,
            "high": 7,
            "critical": 9,
        }
        return severity_scores.get(severity.lower(), 5)

    @classmethod
    def get_severity_from_score(cls, score: float) -> str:
        """Convert 0-10 score to severity level."""
        if score <= 2:
            return "low"
        elif score <= 5:
            return "medium"
        elif score <= 8:
            return "high"
        else:
            return "critical"

    @classmethod
    def calculate_risk_score(
        cls,
        severity: str,
        confidence: float,
        new_risks_count: int = 0,
        escalated_risks_count: int = 0,
    ) -> float:
        """
        Calculate overall risk score.
        
        risk score = severity_weight + confidence_weight + new_risks_bonus + escalated_risks_bonus
        
        Where:
        - severity_weight: 0-10 based on severity level
        - confidence_weight: confidence * 10 (0-10)
        - new_risks_bonus: new_risks_count * 0.5 (capped at 5)
        - escalated_risks_bonus: escalated_risks_count * 1.0 (capped at 5)
        """
        severity_score = cls.get_severity_score(severity)
        confidence_score = confidence * 10
        new_risks_bonus = min(new_risks_count * 0.5, 5.0)
        escalated_risks_bonus = min(escalated_risks_count * 1.0, 5.0)
        
        total = severity_score + confidence_score + new_risks_bonus + escalated_risks_bonus
        return round(total, 2)


def create_classifier() -> RuleBasedClassifier:
    return RuleBasedClassifier()

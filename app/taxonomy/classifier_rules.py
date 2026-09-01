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


class SeverityRules:
    SEVERITY_KEYWORDS = {
        "critical": [
            "existential",
            "bankruptcy",
            "going concern",
            "material weakness",
            "catastrophic",
            "survival",
            "cease operations",
            "insolvency",
        ],
        "high": [
            "significant",
            "material",
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
        "medium": [
            "moderate",
            "potential",
            "possible",
            "may impact",
            "could affect",
            "reasonably possible",
            "likely",
            "expected to",
        ],
        "low": [
            "minor",
            "limited",
            "minimal",
            "unlikely",
            "remote",
            "low probability",
            "immaterial",
            "negligible",
        ],
        "informational": [
            "disclosed for transparency",
            "no impact",
            "routine",
            "for information",
            "no material effect",
        ],
    }

    @classmethod
    def classify_severity(cls, text: str, category: str = None) -> str:
        text_lower = text.lower()
        scores = {}

        for severity, keywords in cls.SEVERITY_KEYWORDS.items():
            scores[severity] = sum(2 if kw in text_lower else 0 for kw in keywords)

        category_boost = {
            "cyber": {"critical": 1, "high": 1},
            "auditor_concern": {"critical": 2, "high": 1},
            "liquidity": {"critical": 1, "high": 1},
            "legal": {"high": 1},
        }

        if category and category in category_boost:
            for sev, boost in category_boost[category].items():
                scores[sev] = scores.get(sev, 0) + boost

        if not any(scores.values()):
            return "medium"

        return max(scores, key=scores.get)


def create_classifier() -> RuleBasedClassifier:
    return RuleBasedClassifier()

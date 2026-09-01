from enum import Enum


class RiskCategory(str, Enum):
    OPERATIONAL = "operational"
    FINANCIAL = "financial"
    REGULATORY = "regulatory"
    STRATEGIC = "strategic"
    CYBER = "cyber"
    CLIMATE = "climate"
    GOVERNANCE = "governance"
    SUPPLY_CHAIN = "supply_chain"
    LEGAL = "legal"
    REPUTATIONAL = "reputational"
    TALENT = "talent"
    TECHNOLOGY = "technology"
    MARKET = "market"
    LIQUIDITY = "liquidity"
    CREDIT = "credit"
    ESG = "esg"
    GEOPOLITICAL = "geopolitical"
    AUDITOR_CONCERN = "auditor_concern"


class RiskSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class ChangeType(str, Enum):
    NEW = "NEW"
    REMOVED = "REMOVED"
    SEVERITY_UP = "SEVERITY_UP"
    SEVERITY_DOWN = "SEVERITY_DOWN"
    MODIFIED = "MODIFIED"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class LLMProvider(str, Enum):
    GROQ = "groq"
    OLLAMA = "ollama"
    CLAUDE = "claude"


class EmbeddingProvider(str, Enum):
    SENTENCE_TRANSFORMERS = "sentence-transformers"
    OPENAI = "openai"


class VectorStoreProvider(str, Enum):
    PGVECTOR = "pgvector"
    PINECONE = "pinecone"


RISK_CATEGORY_KEYWORDS: dict[RiskCategory, list[str]] = {
    RiskCategory.OPERATIONAL: [
        "operational risk",
        "business disruption",
        "process failure",
        "system outage",
        "operational efficiency",
        "business continuity",
        "disaster recovery",
    ],
    RiskCategory.FINANCIAL: [
        "financial risk",
        "revenue decline",
        "profitability",
        "margin pressure",
        "cost increase",
        "financial performance",
        "earnings volatility",
    ],
    RiskCategory.REGULATORY: [
        "regulatory risk",
        "compliance",
        "regulation",
        "regulatory change",
        "legal compliance",
        "statutory",
        "licensing",
        "permit",
    ],
    RiskCategory.STRATEGIC: [
        "strategic risk",
        "competition",
        "market share",
        "strategic initiative",
        "business model",
        "digital transformation",
        "innovation risk",
    ],
    RiskCategory.CYBER: [
        "cyber",
        "cybersecurity",
        "data breach",
        "information security",
        "ransomware",
        "phishing",
        "malware",
        "IT security",
        "data privacy",
    ],
    RiskCategory.CLIMATE: [
        "climate",
        "environmental",
        "carbon",
        "emission",
        "sustainability",
        "climate change",
        "physical risk",
        "transition risk",
        "net zero",
    ],
    RiskCategory.GOVERNANCE: [
        "governance",
        "board",
        "corporate governance",
        "executive compensation",
        "succession",
        "independence",
        "audit committee",
        "related party",
    ],
    RiskCategory.SUPPLY_CHAIN: [
        "supply chain",
        "vendor",
        "supplier",
        "procurement",
        "logistics",
        "single source",
        "concentration risk",
        "third party",
    ],
    RiskCategory.LEGAL: [
        "litigation",
        "lawsuit",
        "legal proceeding",
        "contingent liability",
        "arbitration",
        "settlement",
        "class action",
        "regulatory action",
    ],
    RiskCategory.REPUTATIONAL: [
        "reputation",
        "brand",
        "public perception",
        "media",
        "social media",
        "stakeholder trust",
        "customer confidence",
    ],
    RiskCategory.TALENT: [
        "talent",
        "human capital",
        "key personnel",
        "retention",
        "recruitment",
        "succession planning",
        "skills gap",
        "labor",
    ],
    RiskCategory.TECHNOLOGY: [
        "technology risk",
        "digital",
        "automation",
        "AI",
        "artificial intelligence",
        "legacy system",
        "technical debt",
        "innovation",
    ],
    RiskCategory.MARKET: [
        "market risk",
        "demand",
        "customer",
        "pricing",
        "foreign exchange",
        "commodity price",
        "interest rate",
        "equity price",
    ],
    RiskCategory.LIQUIDITY: [
        "liquidity",
        "cash flow",
        "working capital",
        "funding",
        "solvency",
        "debt maturity",
        "refinancing",
        "covenant",
    ],
    RiskCategory.CREDIT: [
        "credit risk",
        "counterparty",
        "default",
        "credit rating",
        "receivables",
        "bad debt",
        "provision",
        "impairment",
    ],
    RiskCategory.ESG: [
        "ESG",
        "environmental social governance",
        "sustainability",
        "diversity",
        "inclusion",
        "human rights",
        "community",
        "stakeholder",
    ],
    RiskCategory.GEOPOLITICAL: [
        "geopolitical",
        "political risk",
        "trade",
        "sanctions",
        "tariff",
        "war",
        "conflict",
        "instability",
        "regime",
    ],
    RiskCategory.AUDITOR_CONCERN: [
        "auditor",
        "audit opinion",
        "going concern",
        "material weakness",
        "internal control",
        "significant deficiency",
        "emphasis of matter",
    ],
}

SEVERITY_WEIGHTS: dict[RiskSeverity, int] = {
    RiskSeverity.CRITICAL: 5,
    RiskSeverity.HIGH: 4,
    RiskSeverity.MEDIUM: 3,
    RiskSeverity.LOW: 2,
    RiskSeverity.INFORMATIONAL: 1,
}

SEVERITY_COLORS: dict[RiskSeverity, str] = {
    RiskSeverity.CRITICAL: "#dc2626",
    RiskSeverity.HIGH: "#ea580c",
    RiskSeverity.MEDIUM: "#ca8a04",
    RiskSeverity.LOW: "#16a34a",
    RiskSeverity.INFORMATIONAL: "#2563eb",
}

CHANGE_TYPE_COLORS: dict[ChangeType, str] = {
    ChangeType.NEW: "#dc2626",
    ChangeType.REMOVED: "#6b7280",
    ChangeType.SEVERITY_UP: "#ea580c",
    ChangeType.SEVERITY_DOWN: "#16a34a",
    ChangeType.MODIFIED: "#2563eb",
}

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
MIN_CHUNK_SIZE = 100
MAX_CHUNKS_PER_DOC = 500

SIMILARITY_THRESHOLD_NEW_RISK = 0.75
SIMILARITY_THRESHOLD_MATCH = 0.85
SEVERITY_CHANGE_THRESHOLD = 1

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2
REQUEST_TIMEOUT_SECONDS = 120

PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX = 100

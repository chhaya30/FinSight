import re
from dataclasses import dataclass

from app.config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DocumentSection:
    title: str
    level: int
    start_page: int
    end_page: int
    start_char: int
    end_char: int
    content: str
    subsections: list["DocumentSection"]


NORMALIZED_SECTION_MAPPING = {
    "risk factors": [
        "risk factors",
        "principal risks",
        "key risks",
        "material risks",
        "enterprise risks",
        "risk factors and uncertainties",
        "significant risks",
        "major risks",
        "ind as risk disclosure",
        "risk disclosure",
        "risk management",
        "principal risk factors",
    ],
    "md&a": [
        "management's discussion",
        "management discussion",
        "md&a",
        "md and a",
        "management discussion and analysis",
        "management's discussion and analysis",
        "operating and financial review",
        "ofr",
    ],
    "financial statements": [
        "financial statements",
        "consolidated financial statements",
        "standalone financial statements",
        "financial statements and notes",
        "statement of financial position",
        "balance sheet",
        "profit and loss",
        "income statement",
        "cash flow statement",
        "statement of cash flows",
    ],
    "legal proceedings": [
        "legal proceedings",
        "litigation",
        "legal matters",
        "pending litigation",
        "contingent liabilities",
        "legal proceedings and contingencies",
        "lawsuits",
        "legal actions",
    ],
    "business overview": [
        "business overview",
        "our business",
        "business description",
        "overview of business",
        "business model",
        "description of business",
        "about our business",
    ],
    "cybersecurity": [
        "cybersecurity",
        "cyber security",
        "information security",
        "data security",
        "cyber risk",
        "technology risk",
        "it security",
        "information technology security",
    ],
    "esg/sustainability": [
        "esg",
        "sustainability",
        "environmental social governance",
        "climate disclosure",
        "climate change",
        "environmental sustainability",
        "social responsibility",
        "corporate responsibility",
        "non-financial reporting",
        "business responsibility",
        "sustainability report",
        "esg report",
    ],
    "corporate governance": [
        "corporate governance",
        "governance report",
        "board report",
        "governance",
        "board of directors",
        "director governance",
    ],
    "director's report": [
        "director's report",
        "directors' report",
        "board's report",
        "report of the directors",
        "directors report",
    ],
    "auditor's report": [
        "auditor's report",
        "independent auditor",
        "audit report",
        "independent auditor's report",
        "auditors report",
    ],
    "notes to accounts": [
        "notes to accounts",
        "notes to financial statements",
        "significant accounting policies",
        "accounting policies",
        "notes forming part of financial statements",
    ],
}

SECTION_DISPLAY_NAMES = {
    "risk factors": "Risk Factors",
    "md&a": "MD&A",
    "financial statements": "Financial Statements",
    "legal proceedings": "Legal Proceedings",
    "business overview": "Business Overview",
    "cybersecurity": "Cybersecurity",
    "esg/sustainability": "ESG/Sustainability",
    "corporate governance": "Corporate Governance",
    "director's report": "Director's Report",
    "auditor's report": "Auditor's Report",
    "notes to accounts": "Notes to Accounts",
}


def get_normalized_section_name(section_title: str) -> str | None:
    """Map a section title to its normalized canonical name."""
    title_lower = section_title.lower().strip()
    
    for normalized_name, variants in NORMALIZED_SECTION_MAPPING.items():
        for variant in variants:
            if variant in title_lower:
                return normalized_name
    
    return None


def get_section_display_name(normalized_name: str) -> str:
    """Get the proper display name for a normalized section name."""
    return SECTION_DISPLAY_NAMES.get(normalized_name, normalized_name.replace("&", "and").title())


class SectionDetector:
    def __init__(self):
        self.heading_patterns = [
            # SEC-style headings: "ITEM 1A. RISK FACTORS", "ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS"
            (r"^\s*ITEM\s+\d+[A-Z]?\.\s+[A-Z][^.]*$", 1),
            (r"^\s*ITEM\s+\d+[A-Z]?\.\s+[A-Z][A-Z\s&']+$", 1),
            # Standard numbered headings
            (r"^\s*\d+\.\s+[A-Z][^.]*$", 1),
            (r"^\s*\d+\.\d+\s+[A-Z][^.]*$", 2),
            (r"^\s*\d+\.\d+\.\d+\s+[A-Z][^.]*$", 3),
            # ALL CAPS headings
            (r"^\s*[A-Z][A-Z\s]{2,}\s*$", 1),
            # Title case headings
            (r"^\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s*$", 2),
        ]

        self.known_sections = NORMALIZED_SECTION_MAPPING

    def detect_sections(self, pages: list[str]) -> list[DocumentSection]:
        full_text = "\n\n[PAGE_BREAK]\n\n".join(pages)
        sections = self._find_sections(full_text)
        return self._build_hierarchy(sections)

    def _find_sections(self, text: str) -> list[DocumentSection]:
        sections = []
        lines = text.split("\n")
        char_offset = 0

        for _i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                char_offset += len(line) + 1
                continue

            level = self._get_heading_level(line_stripped)
            if level > 0:
                section_title = self._clean_title(line_stripped)
                page_num = self._estimate_page(char_offset, text)

                sections.append(
                    DocumentSection(
                        title=section_title,
                        level=level,
                        start_page=page_num,
                        end_page=page_num,
                        start_char=char_offset,
                        end_char=char_offset,
                        content="",
                        subsections=[],
                    )
                )

            char_offset += len(line) + 1

        self._set_section_boundaries(sections, text)
        return sections

    def _get_heading_level(self, line: str) -> int:
        for pattern, level in self.heading_patterns:
            if re.match(pattern, line):
                return level
        return 0

    def _clean_title(self, title: str) -> str:
        title = re.sub(r"^\s*\d+(\.\d+)*\s+", "", title)
        title = title.strip()
        return title

    def _estimate_page(self, char_offset: int, text: str) -> int:
        before_text = text[:char_offset]
        page_breaks = before_text.count("[PAGE_BREAK]")
        return page_breaks + 1

    def _set_section_boundaries(self, sections: list[DocumentSection], text: str) -> None:
        for i, section in enumerate(sections):
            if i + 1 < len(sections):
                next_section = sections[i + 1]
                section.end_char = next_section.start_char
                section.end_page = next_section.start_page
            else:
                section.end_char = len(text)
                section.end_page = text.count("[PAGE_BREAK]") + 1

            section.content = text[section.start_char : section.end_char].strip()

    def _build_hierarchy(self, sections: list[DocumentSection]) -> list[DocumentSection]:
        root_sections = []
        stack = []

        for section in sections:
            while stack and stack[-1].level >= section.level:
                stack.pop()

            if stack:
                stack[-1].subsections.append(section)
            else:
                root_sections.append(section)

            stack.append(section)

        return root_sections

    def find_risk_section(self, pages: list[str]) -> DocumentSection | None:
        full_text = "\n\n[PAGE_BREAK]\n\n".join(pages).lower()

        risk_keywords = self.known_sections.get("risk factors", [])
        for keyword in risk_keywords:
            if keyword in full_text:
                idx = full_text.index(keyword)
                page = self._estimate_page(idx, full_text)
                context = full_text[max(0, idx - 500) : idx + 5000]

                return DocumentSection(
                    title="Risk Factors",
                    level=1,
                    start_page=page,
                    end_page=page,
                    start_char=idx,
                    end_char=idx + len(context),
                    content=context,
                    subsections=[],
                )

        return None

    def find_section_by_normalized_name(self, pages: list[str], normalized_name: str) -> DocumentSection | None:
        """Find a section by its normalized name (e.g., 'risk factors', 'md&a', 'cybersecurity')."""
        full_text = "\n\n[PAGE_BREAK]\n\n".join(pages).lower()

        keywords = self.known_sections.get(normalized_name.lower(), [])
        for keyword in keywords:
            if keyword in full_text:
                idx = full_text.index(keyword)
                page = self._estimate_page(idx, full_text)
                context = full_text[max(0, idx - 500) : idx + 5000]

                display_name = get_section_display_name(normalized_name)
                return DocumentSection(
                    title=display_name,
                    level=1,
                    start_page=page,
                    end_page=page,
                    start_char=idx,
                    end_char=idx + len(context),
                    content=context,
                    subsections=[],
                )

        return None


class RiskSectionDetector:
    def __init__(self):
        self.risk_indicators = [
            "risk",
            "uncertainty",
            "adverse",
            "material",
            "significant",
            "potential",
            "exposure",
            "vulnerability",
            "threat",
            "challenge",
            "impact",
            "consequence",
            "likelihood",
            "probability",
        ]

        self.risk_category_keywords = {
            "operational": [
                "operational",
                "business disruption",
                "process",
                "system",
                "continuity",
            ],
            "financial": [
                "financial",
                "revenue",
                "profit",
                "margin",
                "cost",
                "earnings",
                "liquidity",
            ],
            "regulatory": [
                "regulatory",
                "compliance",
                "regulation",
                "legal",
                "statutory",
                "license",
            ],
            "strategic": [
                "strategic",
                "competition",
                "market share",
                "innovation",
                "transformation",
            ],
            "cyber": [
                "cyber",
                "data breach",
                "security",
                "information security",
                "ransomware",
                "privacy",
            ],
            "climate": [
                "climate",
                "environmental",
                "carbon",
                "emission",
                "sustainability",
                "net zero",
            ],
            "governance": [
                "governance",
                "board",
                "executive",
                "compensation",
                "succession",
                "audit",
            ],
            "supply_chain": [
                "supply chain",
                "vendor",
                "supplier",
                "procurement",
                "third party",
            ],
            "legal": [
                "litigation",
                "lawsuit",
                "legal proceeding",
                "contingent liability",
                "arbitration",
            ],
            "reputational": [
                "reputation",
                "brand",
                "public perception",
                "media",
                "stakeholder trust",
            ],
            "talent": [
                "talent",
                "human capital",
                "retention",
                "recruitment",
                "succession",
                "skills",
            ],
            "technology": [
                "technology",
                "digital",
                "automation",
                "ai",
                "legacy",
                "technical debt",
            ],
            "market": [
                "market risk",
                "demand",
                "pricing",
                "foreign exchange",
                "commodity",
                "interest rate",
            ],
            "liquidity": [
                "liquidity",
                "cash flow",
                "working capital",
                "funding",
                "solvency",
                "covenant",
            ],
            "credit": [
                "credit risk",
                "counterparty",
                "default",
                "credit rating",
                "receivables",
                "impairment",
            ],
            "esg": [
                "esg",
                "environmental social",
                "diversity",
                "inclusion",
                "human rights",
                "community",
            ],
            "geopolitical": [
                "geopolitical",
                "political risk",
                "trade",
                "sanctions",
                "tariff",
                "war",
            ],
            "auditor_concern": [
                "auditor",
                "audit opinion",
                "going concern",
                "material weakness",
                "internal control",
            ],
        }

    def detect_risk_sections(self, sections: list[DocumentSection]) -> list[DocumentSection]:
        risk_sections = []

        for section in sections:
            if self._is_risk_section(section):
                risk_sections.append(section)
            elif section.subsections:
                sub_risk = self.detect_risk_sections(section.subsections)
                risk_sections.extend(sub_risk)

        return risk_sections

    def _is_risk_section(self, section: DocumentSection) -> bool:
        content_lower = section.content.lower()
        title_lower = section.title.lower()

        if any(kw in title_lower for kw in ["risk", "uncertainty", "threat", "challenge"]):
            return True

        risk_score = sum(1 for kw in self.risk_indicators if kw in content_lower)
        return risk_score >= 3

    def categorize_section(self, section: DocumentSection) -> list[str]:
        content_lower = section.content.lower()
        categories = []

        for category, keywords in self.risk_category_keywords.items():
            if any(kw in content_lower for kw in keywords):
                categories.append(category)

        return categories if categories else ["general"]


def detect_sections(pages: list[str]) -> list[DocumentSection]:
    detector = SectionDetector()
    return detector.detect_sections(pages)


def find_risk_section(pages: list[str]) -> DocumentSection | None:
    detector = SectionDetector()
    return detector.find_risk_section(pages)


def detect_risk_sections(sections: list[DocumentSection]) -> list[DocumentSection]:
    detector = RiskSectionDetector()
    return detector.detect_risk_sections(sections)


def categorize_section(section: DocumentSection) -> list[str]:
    detector = RiskSectionDetector()
    return detector.categorize_section(section)


def find_section_by_normalized_name(pages: list[str], normalized_name: str) -> DocumentSection | None:
    """Find a section by its normalized name (e.g., 'risk factors', 'md&a', 'cybersecurity')."""
    detector = SectionDetector()
    return detector.find_section_by_normalized_name(pages, normalized_name)


def get_all_normalized_section_names() -> list[str]:
    """Get all available normalized section names."""
    return list(NORMALIZED_SECTION_MAPPING.keys())

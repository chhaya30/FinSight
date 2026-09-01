import re
from dataclasses import dataclass

from app.config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DocumentMetadata:
    company_name: str | None = None
    fiscal_year: int | None = None
    sector: str | None = None
    market_cap: float | None = None
    currency: str | None = None
    exchange: str | None = None
    cin: str | None = None
    isin: str | None = None
    reporting_period: str | None = None
    auditor_name: str | None = None
    key_executives: list[str] = None
    financial_highlights: dict[str, float] = None

    def __post_init__(self):
        if self.key_executives is None:
            self.key_executives = []
        if self.financial_highlights is None:
            self.financial_highlights = {}


class MetadataExtractor:
    def __init__(self):
        self.company_patterns = [
            r"(?:Company|Corporation|Ltd|Limited|Inc|PLC)\s*[:\-]?\s*([A-Z][A-Za-z\s&]+)",
            r"^([A-Z][A-Za-z\s&]+(?:Ltd|Limited|Inc|Corporation|PLC))\b",
        ]

        self.year_patterns = [
            r"(?:FY|Fiscal Year|Financial Year|Year Ended)\s*[:\-]?\s*(\d{4})",
            r"(?:Annual Report|Report)\s+(\d{4})",
            r"Year\s+Ended\s+\d{1,2}\w+\s+(\d{4})",
        ]

        self.sector_patterns = [
            r"(?:Sector|Industry)\s*[:\-]?\s*([A-Za-z\s]+)",
            r"Operating in\s+(?:the\s+)?([A-Za-z\s]+)\s+sector",
        ]

        self.financial_patterns = {
            "revenue": [
                r"(?:Revenue|Total Revenue|Net Sales|Turnover)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)",
                r"(?:Revenue|Sales)\s+of\s+([\d,]+(?:\.\d+)?)",
            ],
            "profit": [
                r"(?:Profit|Net Profit|Profit After Tax|PAT)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)",
            ],
            "net_margin": [
                r"(?:Net Margin|Profit Margin)\s*[:\-]?\s*([\d.]+)%",
            ],
            "eps": [
                r"(?:EPS|Earnings Per Share)\s*[:\-]?\s*([\d.]+)",
            ],
        }

        self.cin_pattern = r"(?:CIN|Corporate Identity Number)\s*[:\-]?\s*([A-Z0-9]{21})"
        self.isin_pattern = (
            r"(?:ISIN|International Securities Identification Number)"
            r"\s*[:\-]?\s*([A-Z]{2}[A-Z0-9]{9}\d)"
        )

    def extract(self, text: str, pages: list[str] = None) -> DocumentMetadata:
        metadata = DocumentMetadata()

        first_pages = "\n".join(pages[:5]) if pages else text[:10000]
        full_text = text

        metadata.company_name = self._extract_company_name(first_pages)
        metadata.fiscal_year = self._extract_fiscal_year(first_pages)
        metadata.sector = self._extract_sector(first_pages)
        metadata.currency = self._detect_currency(full_text)
        metadata.exchange = self._detect_exchange(full_text)
        metadata.cin = self._extract_cin(full_text)
        metadata.isin = self._extract_isin(full_text)
        metadata.reporting_period = self._extract_reporting_period(first_pages)
        metadata.auditor_name = self._extract_auditor(full_text)
        metadata.key_executives = self._extract_executives(full_text)
        metadata.financial_highlights = self._extract_financial_highlights(full_text)

        return metadata

    def _extract_company_name(self, text: str) -> str | None:
        for pattern in self.company_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                name = match.group(1).strip()
                if len(name) > 3 and not name.lower().startswith(("the ", "a ", "an ")):
                    return name
        return None

    def _extract_fiscal_year(self, text: str) -> int | None:
        for pattern in self.year_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                year = int(match.group(1))
                if 1990 <= year <= 2030:
                    return year
        return None

    def _extract_sector(self, text: str) -> str | None:
        for pattern in self.sector_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _detect_currency(self, text: str) -> str | None:
        currency_indicators = {
            "INR": ["₹", "Rs.", "INR", "Rupees", "Crore", "Lakh"],
            "USD": ["$", "USD", "US Dollars", "Dollars"],
            "EUR": ["€", "EUR", "Euros"],
            "GBP": ["£", "GBP", "Pounds"],
        }

        scores = {}
        for currency, indicators in currency_indicators.items():
            score = sum(text.count(ind) for ind in indicators)
            if score > 0:
                scores[currency] = score

        return max(scores, key=scores.get) if scores else None

    def _detect_exchange(self, text: str) -> str | None:
        text_lower = text.lower()
        if "bse" in text_lower or "bombay stock exchange" in text_lower:
            return "BSE"
        if "nse" in text_lower or "national stock exchange" in text_lower:
            return "NSE"
        if "sec" in text_lower or "securities and exchange commission" in text_lower:
            return "SEC"
        if "nyse" in text_lower or "new york stock exchange" in text_lower:
            return "NYSE"
        if "nasdaq" in text_lower:
            return "NASDAQ"
        return None

    def _extract_cin(self, text: str) -> str | None:
        match = re.search(self.cin_pattern, text, re.IGNORECASE)
        return match.group(1) if match else None

    def _extract_isin(self, text: str) -> str | None:
        match = re.search(self.isin_pattern, text, re.IGNORECASE)
        return match.group(1) if match else None

    def _extract_reporting_period(self, text: str) -> str | None:
        period_patterns = [
            r"(?:Year Ended|Period Ended)\s+(\d{1,2}\w+\s+\d{4})",
            r"(\d{1,2}\w+\s+\d{4})\s*[-–]\s*(\d{1,2}\w+\s+\d{4})",
        ]

        for pattern in period_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _extract_auditor(self, text: str) -> str | None:
        auditor_patterns = [
            r"(?:Auditor|Independent Auditor)\s*[:\-]?\s*"
            r"([A-Za-z\s&]+(?:LLP|LLP|Chartered Accountants)?)",
            r"Audited by\s+([A-Za-z\s&]+)",
        ]

        for pattern in auditor_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_executives(self, text: str) -> list[str]:
        executives = []
        exec_patterns = [
            r"(?:Chairman|Chairperson|CEO|Managing Director|CFO"
            r"|Chief Financial Officer)\s*[:\-]?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)",
            r"(?:Mr|Ms|Mrs)\.\s+([A-Z][a-z]+\s+[A-Z][a-z]+)"
            r"\s*[,\-]\s*(?:Chairman|CEO|CFO|Director)",
        ]

        for pattern in exec_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            executives.extend(matches)

        return list(set(executives))[:10]

    def _extract_financial_highlights(self, text: str) -> dict[str, float]:
        highlights = {}

        for metric, patterns in self.financial_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    try:
                        value = float(matches[-1].replace(",", ""))
                        highlights[metric] = value
                        break
                    except ValueError:
                        continue

        return highlights


def extract_metadata(text: str, pages: list[str] = None) -> DocumentMetadata:
    extractor = MetadataExtractor()
    return extractor.extract(text, pages)

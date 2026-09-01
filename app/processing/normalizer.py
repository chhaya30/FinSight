import re

from app.config.logging import get_logger

logger = get_logger(__name__)


class DocumentNormalizer:
    def __init__(self):
        self.currency_patterns = {
            "INR": [r"₹", r"Rs\.?", r"INR", r"Indian Rupee"],
            "USD": [r"\$", r"USD", r"US Dollars?"],
            "EUR": [r"€", r"EUR", r"Euros?"],
            "GBP": [r"£", r"GBP", r"Pounds?"],
        }

        self.number_patterns = {
            "crore": r"(\d+(?:\.\d+)?)\s*crore",
            "lakh": r"(\d+(?:\.\d+)?)\s*lakh",
            "million": r"(\d+(?:\.\d+)?)\s*million",
            "billion": r"(\d+(?:\.\d+)?)\s*billion",
            "thousand": r"(\d+(?:\.\d+)?)\s*thousand",
        }

        self.date_patterns = [
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b",
            r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b",
        ]

    def normalize(self, text: str) -> str:
        text = self._normalize_whitespace(text)
        text = self._normalize_unicode(text)
        text = self._normalize_currencies(text)
        text = self._normalize_numbers(text)
        text = self._normalize_dates(text)
        text = self._normalize_percentages(text)
        text = self._normalize_references(text)
        return text

    def _normalize_whitespace(self, text: str) -> str:
        text = re.sub(r"\r\n", "\n", text)
        text = re.sub(r"\r", "\n", text)
        text = re.sub(r"\t", " ", text)
        text = re.sub(r"[ \u00a0]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _normalize_unicode(self, text: str) -> str:
        replacements = {
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2013": "-",
            "\u2014": "-",
            "\u2026": "...",
            "\u00a0": " ",
            "\u200b": "",
            "\u200c": "",
            "\u200d": "",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def _normalize_currencies(self, text: str) -> str:
        for currency, patterns in self.currency_patterns.items():
            for pattern in patterns:
                text = re.sub(
                    pattern,
                    f" {currency} ",
                    text,
                    flags=re.IGNORECASE,
                )
        return text

    def _normalize_numbers(self, text: str) -> str:
        for unit, pattern in self.number_patterns.items():

            def replace_func(match, unit=unit):
                num = float(match.group(1))
                multipliers = {
                    "crore": 10_000_000,
                    "lakh": 100_000,
                    "million": 1_000_000,
                    "billion": 1_000_000_000,
                    "thousand": 1_000,
                }
                value = num * multipliers[unit]
                return f" {value:,.0f} "

            text = re.sub(pattern, replace_func, text, flags=re.IGNORECASE)
        return text

    def _normalize_dates(self, text: str) -> str:
        for pattern in self.date_patterns:
            text = re.sub(pattern, " [DATE] ", text, flags=re.IGNORECASE)
        return text

    def _normalize_percentages(self, text: str) -> str:
        text = re.sub(r"(\d+(?:\.\d+)?)\s*%", r" \1 percent ", text)
        return text

    def _normalize_references(self, text: str) -> str:
        text = re.sub(r"\(see\s+page\s+\d+\)", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\(refer\s+to\s+note\s+\d+\)", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\[\d+\]", "", text)
        return text


class SECBSENormalizer(DocumentNormalizer):
    SEC_TERMS = {
        "form 10-k": "annual report",
        "form 10-q": "quarterly report",
        "form 8-k": "current report",
        "proxy statement": "proxy statement",
        "risk factors": "risk factors",
        "management's discussion": "md&a",
        "md&a": "md&a",
        "md and a": "md&a",
    }

    BSE_TERMS = {
        "annual report": "annual report",
        "director's report": "director's report",
        "corporate governance report": "corporate governance",
        "management discussion": "md&a",
        "business responsibility": "brr",
    }

    def normalize_sector_terms(self, text: str, exchange: str = "BSE") -> str:
        terms = self.SEC_TERMS if exchange.upper() == "SEC" else self.BSE_TERMS

        for term, normalized in terms.items():
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            text = pattern.sub(normalized, text)

        return text

    def normalize_risk_section_headers(self, text: str) -> str:
        risk_headers = [
            r"risk\s+factors?",
            r"principal\s+risks?",
            r"key\s+risks?",
            r"material\s+risks?",
            r"enterprise\s+risks?",
            r"significant\s+risks?",
        ]

        for pattern in risk_headers:
            text = re.sub(
                pattern,
                "RISK FACTORS",
                text,
                flags=re.IGNORECASE,
            )

        return text


def normalize_text(text: str) -> str:
    normalizer = DocumentNormalizer()
    return normalizer.normalize(text)

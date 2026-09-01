import re

from app.config.logging import get_logger

logger = get_logger(__name__)


class TextCleaner:
    def __init__(
        self,
        remove_headers_footers: bool = True,
        remove_page_numbers: bool = True,
        remove_excessive_whitespace: bool = True,
        remove_special_chars: bool = False,
        min_line_length: int = 3,
    ):
        self.remove_headers_footers = remove_headers_footers
        self.remove_page_numbers = remove_page_numbers
        self.remove_excessive_whitespace = remove_excessive_whitespace
        self.remove_special_chars = remove_special_chars
        self.min_line_length = min_line_length

        self.header_footer_patterns = [
            r"^\s*\d+\s*$",
            r"^\s*Page \d+ of \d+\s*$",
            r"^\s*Annual Report\s+\d{4}\s*$",
            r"^\s*Confidential\s*$",
            r"^\s*[A-Z\s]{3,}\s+\d{4}\s*$",
        ]

    def clean(self, text: str) -> str:
        if not text:
            return ""

        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            line = line.rstrip()

            if self.remove_page_numbers and self._is_page_number(line):
                continue

            if self.remove_headers_footers and self._is_header_footer(line):
                continue

            if len(line.strip()) < self.min_line_length:
                continue

            cleaned_lines.append(line)

        text = "\n".join(cleaned_lines)

        if self.remove_excessive_whitespace:
            text = self._normalize_whitespace(text)

        if self.remove_special_chars:
            text = self._remove_special_chars(text)

        return text.strip()

    def clean_pages(self, pages: list[str]) -> list[str]:
        return [self.clean(page) for page in pages]

    def _is_page_number(self, line: str) -> bool:
        line = line.strip()
        return bool(re.match(r"^\d+$", line))

    def _is_header_footer(self, line: str) -> bool:
        line = line.strip()
        for pattern in self.header_footer_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return True
        return False

    def _normalize_whitespace(self, text: str) -> str:
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        text = re.sub(r"\n[ \t]+", "\n", text)
        return text

    def _remove_special_chars(self, text: str) -> str:
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
        text = re.sub(r"[^\w\s\.\,\;\:\!\?\(\)\[\]\{\}\-\'\"]+", " ", text)
        return text


class AdvancedTextCleaner(TextCleaner):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.table_patterns = [
            r"^\s*\|.*\|\s*$",
            r"^\s*\+[-+]+\+\s*$",
        ]
        self.bullet_patterns = [
            r"^\s*[\-\*\•]\s+",
            r"^\s*\d+\.\s+",
            r"^\s*[a-zA-Z]\)\s+",
        ]

    def clean(self, text: str) -> str:
        text = super().clean(text)
        text = self._normalize_bullets(text)
        text = self._mark_tables(text)
        return text

    def _normalize_bullets(self, text: str) -> str:
        lines = text.split("\n")
        normalized = []

        for line in lines:
            for pattern in self.bullet_patterns:
                if re.match(pattern, line):
                    line = re.sub(pattern, "• ", line)
                    break
            normalized.append(line)

        return "\n".join(normalized)

    def _mark_tables(self, text: str) -> str:
        lines = text.split("\n")
        in_table = False
        marked = []

        for line in lines:
            is_table = any(re.match(p, line) for p in self.table_patterns)

            if is_table and not in_table:
                marked.append("[TABLE_START]")
                in_table = True
            elif not is_table and in_table:
                marked.append("[TABLE_END]")
                in_table = False

            marked.append(line)

        if in_table:
            marked.append("[TABLE_END]")

        return "\n".join(marked)


def clean_text(text: str, **kwargs) -> str:
    cleaner = TextCleaner(**kwargs)
    return cleaner.clean(text)


def clean_pages(pages: list[str], **kwargs) -> list[str]:
    cleaner = TextCleaner(**kwargs)
    return cleaner.clean_pages(pages)

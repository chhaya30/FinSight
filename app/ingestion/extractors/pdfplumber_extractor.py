from pathlib import Path

import pdfplumber

from app.config.logging import get_logger
from app.models.document import DocumentMetadata, ExtractedDocument, PageContent

logger = get_logger(__name__)


class PDFPlumberExtractor:
    """Extracts page-wise text content from PDF documents using pdfplumber.

    Better for complex layouts, tables, and forms compared to PyMuPDF.
    """

    def __init__(self, extract_tables: bool = False):
        self.extract_tables = extract_tables

    def extract(self, file_path: Path) -> ExtractedDocument:
        """Extract text content from a PDF document."""
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        if file_path.suffix.lower() != ".pdf":
            raise ValueError(f"Expected a PDF file, got: {file_path.suffix}")

        pages: list[PageContent] = []

        with pdfplumber.open(file_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""

                if self.extract_tables:
                    tables = page.extract_tables()
                    if tables:
                        table_text = self._format_tables(tables)
                        text = f"{text}\n\n[TABLES]\n{table_text}"

                pages.append(
                    PageContent(
                        page_number=page_number,
                        text=text,
                        char_count=len(text),
                    )
                )

        metadata = DocumentMetadata(
            file_name=file_path.name,
            file_path=file_path,
            total_pages=len(pages),
            file_size_bytes=file_path.stat().st_size,
        )

        logger.info(
            "pdf_extracted_pdfplumber",
            file_name=file_path.name,
            pages=len(pages),
            total_chars=sum(p.char_count for p in pages),
        )

        return ExtractedDocument(metadata=metadata, pages=pages)

    def _format_tables(self, tables: list[list[list[str | None]]]) -> str:
        """Format extracted tables as markdown-like text."""
        formatted = []
        for i, table in enumerate(tables):
            formatted.append(f"--- Table {i + 1} ---")
            for row in table:
                if row:
                    formatted.append(" | ".join(str(cell or "") for cell in row))
            formatted.append("")
        return "\n".join(formatted)


class PDFPlumberLayoutExtractor(PDFPlumberExtractor):
    """Extracts text with layout information using pdfplumber."""

    def extract_with_layout(self, file_path: Path) -> ExtractedDocument:
        """Extract text with bounding box and font information."""
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        pages: list[PageContent] = []

        with pdfplumber.open(file_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                words = page.extract_words(
                    keep_blank_chars=True,
                    x_tolerance=3,
                    y_tolerance=3,
                )

                text_parts = []
                for word in words:
                    text_parts.append(word.get("text", ""))

                text = " ".join(text_parts)

                pages.append(
                    PageContent(
                        page_number=page_number,
                        text=text,
                        char_count=len(text),
                    )
                )

        metadata = DocumentMetadata(
            file_name=file_path.name,
            file_path=file_path,
            total_pages=len(pages),
            file_size_bytes=file_path.stat().st_size,
        )

        return ExtractedDocument(metadata=metadata, pages=pages)

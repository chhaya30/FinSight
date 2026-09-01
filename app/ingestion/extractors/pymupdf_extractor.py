from pathlib import Path

import pymupdf

from app.models.document import (
    DocumentMetadata,
    ExtractedDocument,
    PageContent,
)


class PyMuPDFExtractor:
    """Extracts page-wise text content from PDF documents using PyMuPDF."""

    def extract(self, file_path: Path) -> ExtractedDocument:
        """Extract text content from a PDF document."""

        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        if file_path.suffix.lower() != ".pdf":
            raise ValueError(f"Expected a PDF file, got: {file_path.suffix}")

        pages: list[PageContent] = []

        with pymupdf.open(file_path) as pdf:
            for page_number, page in enumerate(pdf, start=1):
                text = page.get_text()

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

        return ExtractedDocument(
            metadata=metadata,
            pages=pages,
        )

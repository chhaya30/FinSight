import hashlib
from pathlib import Path

import pdfplumber
import pymupdf

from app.config.logging import get_logger
from app.models.document import DocumentMetadata, ExtractedDocument, PageContent

logger = get_logger(__name__)


class PDFLoader:
    def __init__(self, use_pymupdf: bool = True):
        self.use_pymupdf = use_pymupdf

    def load(self, file_path: Path) -> ExtractedDocument:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        file_size = file_path.stat().st_size
        file_hash = self._compute_hash(file_path)

        if self.use_pymupdf:
            return self._load_with_pymupdf(file_path, file_size, file_hash)
        else:
            return self._load_with_pdfplumber(file_path, file_size, file_hash)

    def load_from_bytes(self, content: bytes, filename: str) -> ExtractedDocument:
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            return self.load(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    def _load_with_pymupdf(
        self, file_path: Path, file_size: int, file_hash: str
    ) -> ExtractedDocument:
        doc = pymupdf.open(file_path)
        pages = []

        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")
                char_count = len(text)

                pages.append(
                    PageContent(
                        page_number=page_num + 1,
                        text=text,
                        char_count=char_count,
                    )
                )

            metadata = DocumentMetadata(
                file_name=file_path.name,
                file_path=file_path,
                total_pages=len(doc),
                file_size_bytes=file_size,
            )

            logger.info(
                "pdf_loaded_pymupdf",
                file_name=file_path.name,
                pages=len(doc),
                total_chars=sum(p.char_count for p in pages),
            )

            return ExtractedDocument(metadata=metadata, pages=pages)
        finally:
            doc.close()

    def _load_with_pdfplumber(
        self, file_path: Path, file_size: int, file_hash: str
    ) -> ExtractedDocument:
        pages = []

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                char_count = len(text)

                pages.append(
                    PageContent(
                        page_number=page_num + 1,
                        text=text,
                        char_count=char_count,
                    )
                )

            metadata = DocumentMetadata(
                file_name=file_path.name,
                file_path=file_path,
                total_pages=len(pdf.pages),
                file_size_bytes=file_size,
            )

            logger.info(
                "pdf_loaded_pdfplumber",
                file_name=file_path.name,
                pages=len(pdf.pages),
                total_chars=sum(p.char_count for p in pages),
            )

            return ExtractedDocument(metadata=metadata, pages=pages)

    def _compute_hash(self, file_path: Path) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def get_page_count(self, file_path: Path) -> int:
        file_path = Path(file_path)
        if self.use_pymupdf:
            doc = pymupdf.open(file_path)
            count = len(doc)
            doc.close()
            return count
        else:
            with pdfplumber.open(file_path) as pdf:
                return len(pdf.pages)

    def is_scanned(self, file_path: Path, threshold: float = 0.1) -> bool:
        doc = self.load(file_path)
        total_chars = sum(p.char_count for p in doc.pages)
        expected_chars = doc.metadata.total_pages * 1000
        return (total_chars / expected_chars) < threshold if expected_chars > 0 else True

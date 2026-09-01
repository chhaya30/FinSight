from pathlib import Path

from app.config.logging import get_logger
from app.config.settings import get_settings
from app.ingestion.loaders.pdf_loader import PDFLoader
from app.ingestion.ocr.ocr_engine import OCREngine
from app.models.document import ExtractedDocument, PageContent

logger = get_logger(__name__)


class FallbackRouter:
    def __init__(
        self,
        pdf_loader: PDFLoader | None = None,
        ocr_engine: OCREngine | None = None,
        scanned_threshold: float = 0.1,
    ):
        self.pdf_loader = pdf_loader or PDFLoader()
        self.ocr_engine = ocr_engine or OCREngine()
        self.scanned_threshold = scanned_threshold
        self.settings = get_settings()

    def process(self, file_path: Path) -> ExtractedDocument:
        file_path = Path(file_path)

        logger.info("processing_document", file_name=file_path.name)

        if not self.settings.OCR_ENABLED:
            return self.pdf_loader.load(file_path)

        try:
            doc = self.pdf_loader.load(file_path)

            if self._is_scanned(doc):
                logger.info("document_detected_as_scanned", file_name=file_path.name)
                return self._process_with_ocr(file_path)

            logger.info("document_processed_with_text_extraction", file_name=file_path.name)
            return doc
        except Exception as e:
            logger.error("text_extraction_failed", file_name=file_path.name, error=str(e))
            if self.settings.OCR_ENABLED:
                logger.info("falling_back_to_ocr", file_name=file_path.name)
                return self._process_with_ocr(file_path)
            raise

    def _is_scanned(self, doc: ExtractedDocument) -> bool:
        total_chars = sum(p.char_count for p in doc.pages)
        expected_chars = doc.metadata.total_pages * 1000

        if expected_chars == 0:
            return True

        char_ratio = total_chars / expected_chars
        return char_ratio < self.scanned_threshold

    def _process_with_ocr(self, file_path: Path) -> ExtractedDocument:
        if not self.ocr_engine.is_available():
            logger.warning("ocr_not_available_returning_empty", file_name=file_path.name)
            return self._create_empty_document(file_path)

        try:
            return self.ocr_engine.process_pdf(file_path)
        except Exception as e:
            logger.error("ocr_failed", file_name=file_path.name, error=str(e))
            return self._create_empty_document(file_path)

    def _create_empty_document(self, file_path: Path) -> ExtractedDocument:
        from app.models.document import DocumentMetadata

        return ExtractedDocument(
            metadata=DocumentMetadata(
                file_name=file_path.name,
                file_path=file_path,
                total_pages=0,
                file_size_bytes=file_path.stat().st_size if file_path.exists() else 0,
            ),
            pages=[],
        )


class AdaptiveFallbackRouter(FallbackRouter):
    def __init__(
        self,
        pdf_loader: PDFLoader | None = None,
        ocr_engine: OCREngine | None = None,
        scanned_threshold: float = 0.1,
        min_text_per_page: int = 100,
    ):
        super().__init__(pdf_loader, ocr_engine, scanned_threshold)
        self.min_text_per_page = min_text_per_page

    def process(self, file_path: Path) -> ExtractedDocument:
        file_path = Path(file_path)

        logger.info("processing_document_adaptive", file_name=file_path.name)

        if not self.settings.OCR_ENABLED:
            return self.pdf_loader.load(file_path)

        try:
            doc = self.pdf_loader.load(file_path)

            if self._needs_ocr(doc):
                logger.info("document_needs_ocr", file_name=file_path.name)
                ocr_doc = self._process_with_ocr(file_path)
                return self._merge_results(doc, ocr_doc)

            logger.info("document_processed_with_text_extraction", file_name=file_path.name)
            return doc
        except Exception as e:
            logger.error("text_extraction_failed", file_name=file_path.name, error=str(e))
            if self.settings.OCR_ENABLED:
                logger.info("falling_back_to_ocr", file_name=file_path.name)
                return self._process_with_ocr(file_path)
            raise

    def _needs_ocr(self, doc: ExtractedDocument) -> bool:
        if doc.metadata.total_pages == 0:
            return True

        total_chars = sum(p.char_count for p in doc.pages)
        expected_chars = doc.metadata.total_pages * 1000

        if expected_chars == 0:
            return True

        overall_ratio = total_chars / expected_chars
        if overall_ratio < self.scanned_threshold:
            return True

        low_text_pages = sum(1 for p in doc.pages if p.char_count < self.min_text_per_page)
        low_text_ratio = low_text_pages / doc.metadata.total_pages

        return low_text_ratio > 0.3

    def _merge_results(
        self, text_doc: ExtractedDocument, ocr_doc: ExtractedDocument
    ) -> ExtractedDocument:
        merged_pages = []
        max_pages = max(text_doc.metadata.total_pages, ocr_doc.metadata.total_pages)

        for i in range(max_pages):
            text_page = text_doc.pages[i] if i < len(text_doc.pages) else None
            ocr_page = ocr_doc.pages[i] if i < len(ocr_doc.pages) else None

            if text_page and text_page.char_count >= self.min_text_per_page:
                merged_pages.append(text_page)
            elif ocr_page and ocr_page.char_count > 0:
                merged_pages.append(ocr_page)
            elif text_page:
                merged_pages.append(text_page)
            elif ocr_page:
                merged_pages.append(ocr_page)
            else:
                merged_pages.append(PageContent(page_number=i + 1, text="", char_count=0))

        return ExtractedDocument(
            metadata=text_doc.metadata,
            pages=merged_pages,
        )


def create_fallback_router(**kwargs) -> FallbackRouter:
    return FallbackRouter(**kwargs)


def create_adaptive_fallback_router(**kwargs) -> AdaptiveFallbackRouter:
    return AdaptiveFallbackRouter(**kwargs)

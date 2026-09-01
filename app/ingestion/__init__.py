from app.ingestion.extractors.extractor_factory import (
    BaseExtractor,
    ExtractorFactory,
    ExtractorType,
    get_extractor,
)
from app.ingestion.extractors.pdfplumber_extractor import (
    PDFPlumberExtractor,
    PDFPlumberLayoutExtractor,
)
from app.ingestion.extractors.pymupdf_extractor import PyMuPDFExtractor
from app.ingestion.loaders.pdf_loader import PDFLoader
from app.ingestion.ocr.fallback_router import (
    AdaptiveFallbackRouter,
    FallbackRouter,
    create_adaptive_fallback_router,
    create_fallback_router,
)
from app.ingestion.ocr.ocr_engine import OCREngine, TesseractOCREngine, create_ocr_engine

__all__ = [
    "PDFLoader",
    "PyMuPDFExtractor",
    "PDFPlumberExtractor",
    "PDFPlumberLayoutExtractor",
    "ExtractorType",
    "BaseExtractor",
    "ExtractorFactory",
    "get_extractor",
    "OCREngine",
    "TesseractOCREngine",
    "create_ocr_engine",
    "FallbackRouter",
    "AdaptiveFallbackRouter",
    "create_fallback_router",
    "create_adaptive_fallback_router",
]

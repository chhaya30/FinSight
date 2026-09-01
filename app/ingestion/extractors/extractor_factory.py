from abc import ABC, abstractmethod
from enum import Enum
from importlib.util import find_spec
from pathlib import Path

from app.config.logging import get_logger
from app.models.document import ExtractedDocument

logger = get_logger(__name__)


class ExtractorType(str, Enum):
    PYMUPDF = "pymupdf"
    PDFPLUMBER = "pdfplumber"
    AUTO = "auto"


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, file_path: Path) -> ExtractedDocument:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass


class ExtractorFactory:
    _extractors = {}

    @classmethod
    def register(cls, extractor_type: ExtractorType, extractor_class):
        cls._extractors[extractor_type] = extractor_class

    @classmethod
    def get_extractor(
        cls, extractor_type: ExtractorType = ExtractorType.AUTO, **kwargs
    ) -> BaseExtractor:
        if extractor_type == ExtractorType.AUTO:
            extractor_type = cls._detect_best_extractor()

        if extractor_type not in cls._extractors:
            raise ValueError(f"Unknown extractor type: {extractor_type}")

        extractor_class = cls._extractors[extractor_type]
        return extractor_class(**kwargs)

    @classmethod
    def _detect_best_extractor(cls) -> ExtractorType:
        if find_spec("pymupdf") is not None:
            return ExtractorType.PYMUPDF

        if find_spec("pdfplumber") is not None:
            return ExtractorType.PDFPLUMBER

        raise RuntimeError("No PDF extraction library available")

    @classmethod
    def available_extractors(cls) -> list:
        return list(cls._extractors.keys())


def get_extractor(extractor_type: ExtractorType = ExtractorType.AUTO, **kwargs) -> BaseExtractor:
    return ExtractorFactory.get_extractor(extractor_type, **kwargs)


ExtractorFactory.register(
    ExtractorType.PYMUPDF,
    "app.ingestion.extractors.pymupdf_extractor:PyMuPDFExtractor",
)
ExtractorFactory.register(
    ExtractorType.PDFPLUMBER,
    "app.ingestion.extractors.pdfplumber_extractor:PDFPlumberExtractor",
)

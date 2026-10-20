import subprocess
import tempfile
import shutil
from pathlib import Path

import pymupdf

from app.config.logging import get_logger
from app.config.settings import get_settings
from app.models.document import DocumentMetadata, ExtractedDocument, PageContent

logger = get_logger(__name__)


class OCREngine:
    def __init__(
        self,
        language: str = "eng",
        dpi: int = 300,
        tesseract_cmd: str | None = None,
    ):
        self.language = language
        self.dpi = dpi
        self.tesseract_cmd = tesseract_cmd or get_settings().TESSERACT_CMD or "tesseract"
        self._check_tesseract()

    def _check_tesseract(self) -> None:
        try:
            subprocess.run(
                [self.tesseract_cmd, "--version"],
                capture_output=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning(
                "tesseract_not_found",
                tesseract_cmd=self.tesseract_cmd,
            )

    def process_pdf(self, file_path: Path) -> ExtractedDocument:
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        doc = pymupdf.open(file_path)
        pages = []

        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=self.dpi)

                image_dir = Path(tempfile.mkdtemp(prefix="finsight_page_"))
                img_path = image_dir / "page.png"
                pix.save(str(img_path))

                try:
                    text = self._ocr_image(img_path)
                finally:
                    shutil.rmtree(image_dir, ignore_errors=True)

                pages.append(
                    PageContent(
                        page_number=page_num + 1,
                        text=text,
                        char_count=len(text),
                    )
                )

            metadata = DocumentMetadata(
                file_name=file_path.name,
                file_path=file_path,
                total_pages=len(doc),
                file_size_bytes=file_path.stat().st_size,
                extraction_method="tesseract_ocr",
                ocr_used=True,
            )

            logger.info(
                "pdf_ocr_completed",
                file_name=file_path.name,
                pages=len(doc),
                total_chars=sum(p.char_count for p in pages),
            )

            return ExtractedDocument(metadata=metadata, pages=pages)
        finally:
            doc.close()

    def process_image(self, file_path: Path) -> str:
        return self._ocr_image(file_path)

    def _ocr_image(self, image_path: Path) -> str:
        output_dir = Path(tempfile.mkdtemp(prefix="finsight_ocr_"))
        output_base = output_dir / "result"

        try:
            cmd = [
                self.tesseract_cmd,
                str(image_path),
                str(output_base),
                "-l",
                self.language,
                "--psm",
                "6",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                logger.error(
                    "tesseract_failed",
                    error=result.stderr,
                    image_path=str(image_path),
                )
                return ""

            output_file = output_base.with_suffix(".txt")
            if output_file.exists():
                return output_file.read_text(encoding="utf-8")
            return ""
        except subprocess.TimeoutExpired:
            logger.error("tesseract_timeout", image_path=str(image_path))
            return ""
        except Exception as e:
            logger.error("tesseract_error", error=str(e), image_path=str(image_path))
            return ""
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)

    def is_available(self) -> bool:
        try:
            subprocess.run(
                [self.tesseract_cmd, "--version"],
                capture_output=True,
                check=True,
            )
            return True
        except Exception:
            return False


class TesseractOCREngine(OCREngine):
    """Tesseract-based OCR engine with enhanced configuration."""

    def __init__(
        self,
        language: str = "eng",
        dpi: int = 300,
        tesseract_cmd: str | None = None,
        config: str = "",
    ):
        super().__init__(language, dpi, tesseract_cmd)
        self.config = config

    def _ocr_image(self, image_path: Path) -> str:
        output_dir = Path(tempfile.mkdtemp(prefix="finsight_ocr_"))
        output_base = output_dir / "result"

        try:
            cmd = [
                self.tesseract_cmd,
                str(image_path),
                str(output_base),
                "-l",
                self.language,
                "--psm",
                "6",
            ]

            if self.config:
                cmd.extend(self.config.split())

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                logger.error(
                    "tesseract_failed",
                    error=result.stderr,
                    image_path=str(image_path),
                )
                return ""

            output_file = output_base.with_suffix(".txt")
            if output_file.exists():
                return output_file.read_text(encoding="utf-8")
            return ""
        except Exception as e:
            logger.error("tesseract_error", error=str(e), image_path=str(image_path))
            return ""
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)


def create_ocr_engine(**kwargs) -> OCREngine:
    return OCREngine(**kwargs)

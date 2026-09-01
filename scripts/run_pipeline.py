#!/usr/bin/env python3
"""Script to run the risk analysis pipeline on a processed report."""

import asyncio
import argparse
from uuid import UUID

from app.config.settings import get_settings
from app.config.logging import setup_logging, get_logger
from app.db.session import init_db, db
from app.db.base import Report, RiskItem
from app.risk_engine import create_pipeline
from app.ingestion import create_adaptive_fallback_router
from app.processing import clean_text, normalize_text, detect_sections
from app.models.document import PageContent

logger = get_logger(__name__)


async def run_pipeline(report_id: UUID):
    settings = get_settings()
    setup_logging()

    await init_db()

    async with db.session() as session:
        report = await session.get(Report, report_id)
        if not report:
            logger.error("report_not_found", report_id=str(report_id))
            return

        logger.info("running_pipeline", report_id=str(report_id), file=report.source_file)

        file_path = Path(settings.UPLOAD_DIR) / report.source_file
        if not file_path.exists():
            logger.error("file_not_found", path=str(file_path))
            return

        fallback_router = create_adaptive_fallback_router()
        extracted_doc = fallback_router.process(file_path)

        pages = [page.text for page in extracted_doc.pages]
        cleaned_pages = [clean_text(page) for page in pages]
        normalized_pages = [normalize_text(page) for page in cleaned_pages]

        page_contents = [
            PageContent(page_number=i+1, text=page, char_count=len(page))
            for i, page in enumerate(normalized_pages)
        ]

        pipeline = create_pipeline()
        result = pipeline.run(page_contents, str(report_id))

        for risk in result.risks:
            risk_model = RiskItem(
                report_id=report_id,
                category=risk.category,
                severity=risk.severity,
                confidence_score=risk.confidence_score,
                summary=risk.summary,
                source_page=risk.candidate.source_page,
                source_paragraph=risk.candidate.text[:500],
                entities=[e.model_dump() for e in risk.entities],
                metadata={
                    "source_section": risk.candidate.source_section,
                    "paragraph_index": risk.candidate.paragraph_index,
                },
            )
            session.add(risk_model)

        report.processing_status = "completed"
        report.pages = len(pages)
        await session.commit()

        logger.info("pipeline_completed", report_id=str(report_id), risks=len(result.risks))

    await db.close()


def main():
    parser = argparse.ArgumentParser(description="Run risk analysis pipeline")
    parser.add_argument("report_id", type=UUID, help="Report UUID")

    args = parser.parse_args()

    asyncio.run(run_pipeline(args.report_id))


if __name__ == "__main__":
    main()
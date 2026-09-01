#!/usr/bin/env python3
"""Script to ingest annual reports from a directory."""

import asyncio
import argparse
from pathlib import Path
from uuid import UUID

from app.config.settings import get_settings
from app.config.logging import setup_logging, get_logger
from app.db.session import init_db, db
from app.db.base import Company, Report
from app.ingestion import create_adaptive_fallback_router
from app.processing import clean_text, normalize_text, detect_sections
from app.risk_engine import create_pipeline
from app.models.document import PageContent

logger = get_logger(__name__)


async def ingest_reports(
    directory: Path,
    company_name: str,
    fiscal_year: int,
    sector: str = None,
):
    settings = get_settings()
    setup_logging()

    await init_db()

    async with db.session() as session:
        company = await session.execute(
            Company.__table__.select().where(Company.name == company_name)
        )
        company = company.scalar_one_or_none()

        if not company:
            company = Company(name=company_name, sector=sector)
            session.add(company)
            await session.flush()

        pdf_files = list(directory.glob("*.pdf"))
        logger.info("found_pdfs", count=len(pdf_files))

        for pdf_file in pdf_files:
            report = await session.execute(
                Report.__table__.select().where(
                    Report.company_id == company.id,
                    Report.fiscal_year == fiscal_year,
                    Report.source_file == pdf_file.name,
                )
            )
            report = report.scalar_one_or_none()

            if report:
                logger.info("report_exists_skipping", file=pdf_file.name)
                continue

            file_hash = ""
            import hashlib
            with open(pdf_file, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()

            report = Report(
                company_id=company.id,
                fiscal_year=fiscal_year,
                source_file=pdf_file.name,
                source_file_hash=file_hash,
                file_size_bytes=pdf_file.stat().st_size,
                processing_status="pending",
            )
            session.add(report)
            await session.flush()

            try:
                fallback_router = create_adaptive_fallback_router()
                extracted_doc = fallback_router.process(pdf_file)

                pages = [page.text for page in extracted_doc.pages]
                cleaned_pages = [clean_text(page) for page in pages]
                normalized_pages = [normalize_text(page) for page in cleaned_pages]

                sections = detect_sections(normalized_pages)

                page_contents = [
                    PageContent(page_number=i+1, text=page, char_count=len(page))
                    for i, page in enumerate(normalized_pages)
                ]

                pipeline = create_pipeline()
                result = pipeline.run(page_contents, str(report.id))

                report.processing_status = "completed"
                report.pages = len(pages)

                from app.db.base import RiskItem
                for risk in result.risks:
                    risk_model = RiskItem(
                        report_id=report.id,
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

                logger.info("report_processed", file=pdf_file.name, risks=len(result.risks))

            except Exception as e:
                report.processing_status = "failed"
                report.error_message = str(e)
                logger.error("report_processing_failed", file=pdf_file.name, error=str(e))

            await session.commit()

    await db.close()
    logger.info("ingestion_complete")


def main():
    parser = argparse.ArgumentParser(description="Ingest annual reports")
    parser.add_argument("directory", type=Path, help="Directory containing PDF files")
    parser.add_argument("company", type=str, help="Company name")
    parser.add_argument("year", type=int, help="Fiscal year")
    parser.add_argument("--sector", type=str, help="Company sector")

    args = parser.parse_args()

    asyncio.run(ingest_reports(args.directory, args.company, args.year, args.sector))


if __name__ == "__main__":
    main()
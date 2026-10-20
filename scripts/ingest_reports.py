#!/usr/bin/env python3
"""Script to ingest annual reports from a directory."""

import asyncio
import argparse
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from app.config.settings import get_settings
from app.config.logging import setup_logging, get_logger
from app.db.session import init_db, db
from app.db.base import Company, Report, FinancialSnapshot
from app.ingestion import create_adaptive_fallback_router
from app.processing import clean_text, normalize_text, detect_sections
from app.risk_engine import create_pipeline
from app.intelligence.financial_health import FinancialSnapshotExtractor
from app.models.document import PageContent

logger = get_logger(__name__)


async def ingest_reports(
    directory: Path,
    company_name: str,
    fiscal_year: int,
    sector: str = None,
    file_name: str = None,
):
    settings = get_settings()
    setup_logging()

    await init_db()

    async with db.session() as session:
        company = await session.execute(
            select(Company).where(Company.name == company_name)
        )
        company = company.scalar_one_or_none()

        if not company:
            company = Company(name=company_name, sector=sector)
            session.add(company)
            await session.flush()

        pdf_files = list(directory.glob("*.pdf"))
        if file_name:
            pdf_files = [f for f in pdf_files if f.name == file_name]
        logger.info("found_pdfs", count=len(pdf_files))

        for pdf_file in pdf_files:
            report = await session.execute(
                select(Report).where(
                    Report.company_id == company.id,
                    Report.fiscal_year == fiscal_year,
                    Report.source_file_name == pdf_file.name,
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
                source_file_name=pdf_file.name,
                source_file=str(pdf_file),
                file_hash=file_hash,
                file_size_bytes=pdf_file.stat().st_size,
                processing_status="uploaded",
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
                    entities_dump = [
                        e.model_dump() if hasattr(e, "model_dump") else dict(e)
                        for e in (risk.entities or [])
                    ]
                    # Convert list to dict for JSON column
                    entities_dict = {str(i): entity for i, entity in enumerate(entities_dump)}
                    risk_model = RiskItem(
                        report_id=str(report.id),
                        company_id=report.company_id,
                        category=risk.category,
                        severity=risk.severity,
                        confidence_score=risk.confidence_score,
                        summary=risk.summary,
                        risk_title=risk.summary[:200],
                        source_page=risk.candidate.source_page,
                        source_paragraph=risk.candidate.text[:500],
                        source_text_hash=risk.candidate.source_text_hash,
                        entities=entities_dict,
                        extra_metadata={
                            "source_section": risk.candidate.source_section,
                            "paragraph_index": risk.candidate.paragraph_index,
                        },
                    )
                    session.add(risk_model)

                logger.info("report_processed", file=pdf_file.name, risks=len(result.risks))

                # Extract and save financial snapshot
                try:
                    extractor = FinancialSnapshotExtractor()
                    snapshot = extractor.extract(
                        normalized_pages,
                        fiscal_year,
                        pdf_file.name,
                        report_id=str(report.id),
                        company_id=str(company.id),
                    )
                    # Convert Pydantic FinancialSnapshot to ORM FinancialSnapshot
                    orm_snapshot = FinancialSnapshot(
                        company_id=company.id,
                        fiscal_year=snapshot.report_year,
                        currency="INR",
                        data_source="pdf_extraction",
                        extra_metadata={"document_id": snapshot.document_id},
                    )
                    # Map extracted metrics to ORM fields
                    metric_map = {
                        "revenue": "revenue",
                        "net_income": "profit",
                        "total_assets": "total_assets",
                        "total_liabilities": "total_liabilities",
                        "cash_and_equivalents": "cash_flow",
                        "debt": "total_debt",
                        "market_cap": "market_cap",
                        "eps": "eps",
                        "roe": "roe",
                    }
                    for metric in snapshot.metrics.values():
                        orm_field = metric_map.get(metric.metric_name)
                        if orm_field and metric.value is not None:
                            setattr(orm_snapshot, orm_field, metric.value)
                    
                    # Calculate net_margin if revenue and profit available
                    if orm_snapshot.revenue and orm_snapshot.profit and orm_snapshot.revenue != 0:
                        orm_snapshot.net_margin = round(orm_snapshot.profit / orm_snapshot.revenue * 100, 2)
                    
                    # Calculate debt_equity if total_debt and total_assets available
                    if orm_snapshot.total_debt and orm_snapshot.total_assets and orm_snapshot.total_assets != 0:
                        orm_snapshot.debt_equity = round(orm_snapshot.total_debt / (orm_snapshot.total_assets - orm_snapshot.total_debt), 2) if (orm_snapshot.total_assets - orm_snapshot.total_debt) != 0 else None
                    
                    session.add(orm_snapshot)
                    logger.info("financial_snapshot_saved", file=pdf_file.name)

                except Exception as e:
                    logger.warning("financial_snapshot_extraction_failed", file=pdf_file.name, error=str(e))

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
    parser.add_argument("--file", type=str, help="Specific PDF file to process (optional)")

    args = parser.parse_args()

    asyncio.run(ingest_reports(args.directory, args.company, args.year, args.sector, args.file))


if __name__ == "__main__":
    main()
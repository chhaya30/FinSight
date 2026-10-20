#!/usr/bin/env python3
"""Generate ingestion report for processed PDFs."""

import asyncio
from pathlib import Path
from sqlalchemy import select, func

from app.config.settings import get_settings
from app.config.logging import setup_logging, get_logger
from app.db.session import init_db, db
from app.db.base import Company, Report, RiskItem, DocumentChunk

logger = get_logger(__name__)


async def generate_ingestion_report():
    settings = get_settings()
    setup_logging()

    await init_db()

    async with db.session() as session:
        # Get all reports with their company info
        reports_result = await session.execute(
            select(Report, Company.name, Company.sector)
            .join(Company, Report.company_id == Company.id)
            .order_by(Company.name, Report.fiscal_year)
        )
        reports = reports_result.all()

        print("=" * 80)
        print("REAL INGESTION REPORT")
        print("=" * 80)
        print()

        for report, company_name, sector in reports:
            # Get chunks count
            chunks_result = await session.execute(
                select(func.count(DocumentChunk.id))
                .where(DocumentChunk.report_id == str(report.id))
            )
            chunks_count = chunks_result.scalar()

            # Get risks count
            risks_result = await session.execute(
                select(func.count(RiskItem.id))
                .where(RiskItem.report_id == str(report.id))
            )
            risks_count = risks_result.scalar()

            # Get embedding dimension from first chunk
            chunk_result = await session.execute(
                select(DocumentChunk.embedding)
                .where(DocumentChunk.report_id == str(report.id))
                .limit(1)
            )
            chunk = chunk_result.first()
            embedding_dim = len(chunk[0]) if chunk and chunk[0] else "N/A"

            print(f"Company: {company_name}")
            print(f"  Sector: {sector or 'N/A'}")
            print(f"  Year: {report.fiscal_year}")
            print(f"  Report ID: {report.id}")
            print(f"  File: {report.source_file_name}")
            print(f"  File Size: {report.file_size_bytes:,} bytes ({report.file_size_bytes/1024/1024:.2f} MB)")
            print(f"  Pages: {report.pages or 'N/A'}")
            print(f"  Characters Extracted: {report.extra_metadata.get('total_chars', 'N/A') if report.extra_metadata else 'N/A'}")
            print(f"  Chunks Created: {chunks_count}")
            print(f"  Embedding Dimension: {embedding_dim}")
            print(f"  Risks Extracted: {risks_count}")
            print(f"  Processing Status: {report.processing_status}")
            print(f"  Processing Error: {report.processing_error or 'None'}")
            print(f"  OCR Used: {'Yes' if report.extra_metadata and report.extra_metadata.get('ocr_used') else 'No'}")
            print()

        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        
        total_reports = len(reports)
        total_pages = sum(r.pages or 0 for r, _, _ in reports)
        total_chars = sum(r.extra_metadata.get('total_chars', 0) if r.extra_metadata else 0 for r, _, _ in reports)
        
        # Get total chunks and risks
        total_chunks_result = await session.execute(select(func.count(DocumentChunk.id)))
        total_chunks = total_chunks_result.scalar()
        
        total_risks_result = await session.execute(select(func.count(RiskItem.id)))
        total_risks = total_risks_result.scalar()
        
        completed = sum(1 for r, _, _ in reports if r.processing_status == "completed")
        failed = sum(1 for r, _, _ in reports if r.processing_status == "failed")
        
        print(f"Total Reports: {total_reports}")
        print(f"  Completed: {completed}")
        print(f"  Failed: {failed}")
        print(f"Total Pages: {total_pages}")
        print(f"Total Characters: {total_chars:,}")
        print(f"Total Chunks: {total_chunks}")
        print(f"Total Risks: {total_risks}")
        print()

    await db.close()


if __name__ == "__main__":
    asyncio.run(generate_ingestion_report())
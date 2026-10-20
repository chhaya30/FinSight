import hashlib
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config.logging import get_logger
from app.config.settings import get_settings
from app.db.base import Company, Report
from app.db.session import get_db_session
from app.ingestion import create_adaptive_fallback_router
from app.models.document import (
    DocumentListResponse,
    DocumentProcessingStatus,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.models.report_metadata import (
    merge_report_metadata,
    normalize_country,
    normalize_market,
    normalize_report_type,
)
from app.processing import chunk_document, clean_text, detect_sections, normalize_text
from app.processing.metadata_extractor import extract_metadata
from app.risk_engine import create_pipeline

logger = get_logger(__name__)

router = APIRouter()

UPLOAD_DIR = Path(get_settings().UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_MARKETS = {"SEC", "BSE", "NSE", "BSE_NSE"}


async def process_document_background(document_id: UUID):
    _ = get_settings()
    from app.db.session import db

    async with db.session() as session:
        report = await session.get(Report, document_id)
        if not report:
            return

        report.processing_status = "processing"
        await session.commit()

        try:
            file_path = UPLOAD_DIR / report.source_file

            fallback_router = create_adaptive_fallback_router()
            extracted_doc = fallback_router.process(file_path)

            if not extracted_doc.pages or not any(page.text.strip() for page in extracted_doc.pages):
                error_code = extracted_doc.metadata.processing_error or "NO_TEXT_EXTRACTED"
                raise RuntimeError(error_code)

            pages = [page.text for page in extracted_doc.pages]
            cleaned_pages = [clean_text(page) for page in pages]
            normalized_pages = [normalize_text(page) for page in cleaned_pages]

            extracted_metadata = extract_metadata("\n".join(normalized_pages), normalized_pages)
            current_metadata = report.extra_metadata or {}
            report.extra_metadata = merge_report_metadata(
                explicit=current_metadata,
                extracted={
                    "exchange": extracted_metadata.exchange,
                    "isin": extracted_metadata.isin,
                    "cin": extracted_metadata.cin,
                    "currency": extracted_metadata.currency,
                    "sector": extracted_metadata.sector,
                    "reporting_period": extracted_metadata.reporting_period,
                    "auditor_name": extracted_metadata.auditor_name,
                },
            ).model_dump(exclude_none=True)

            _ = detect_sections(normalized_pages)

            # 1. Chunking + Embedding + Vector Store Persistence
            from app.retrieval.embedding_pipeline import create_embedding_pipeline

            embedding_pipeline = create_embedding_pipeline()
            chunks = await embedding_pipeline.process_and_store_chunks(
                db=session,
                report_id=report.id,
                company_id=report.company_id,
                fiscal_year=report.fiscal_year,
                text_or_pages=normalized_pages,
            )

            # 2. Risk Extraction + Risk Persistence
            from app.db.base import RiskItem
            from app.models.document import PageContent

            page_contents = [
                PageContent(page_number=i + 1, text=page, char_count=len(page))
                for i, page in enumerate(normalized_pages)
            ]

            pipeline = create_pipeline()
            result = pipeline.run(page_contents, str(document_id))

            for risk_item in result.risks:
                entities_dump = [
                    e.model_dump() if hasattr(e, "model_dump") else dict(e)
                    for e in (risk_item.entities or [])
                ]
                db_risk = RiskItem(
                    report_id=str(report.id),
                    category=risk_item.category,
                    severity=risk_item.severity,
                    confidence_score=risk_item.confidence_score,
                    summary=risk_item.summary,
                    source_page=risk_item.source_page,
                    source_paragraph=risk_item.source_paragraph,
                    source_text_hash=risk_item.source_text_hash,
                    entities=entities_dump,
                    extra_metadata=risk_item.metadata or {},
                )
                session.add(db_risk)

            report.processing_status = "completed"
            report.pages = len(pages)
            await session.commit()

            logger.info(
                "document_processed",
                document_id=str(document_id),
                chunks=len(chunks),
                risks=len(result.risks),
            )

        except Exception as e:
            report.processing_status = "failed"
            report.error_message = str(e)
            await session.commit()
            logger.error("document_processing_failed", document_id=str(document_id), error=str(e))


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    company_id: UUID = Query(...),
    fiscal_year: int = Query(...),
    market: str | None = Query(None, description="Market (SEC, BSE, NSE, or BSE_NSE)"),
    country: str | None = Query(None),
    report_type: str = Query("annual_report"),
    ticker: str | None = Query(None, max_length=32),
    sector: str | None = Query(None, max_length=100),
    exchange: str | None = Query(None, max_length=50),
    currency: str | None = Query(None, max_length=8),
    source_url: str | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    settings = get_settings()

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    if fiscal_year < 1900 or fiscal_year > 2100:
        raise HTTPException(status_code=422, detail="fiscal_year must be between 1900 and 2100")

    normalized_market = normalize_market(market)
    normalized_country = normalize_country(country)
    normalized_report_type = normalize_report_type(report_type)
    if normalized_market not in ALLOWED_MARKETS | {None}:
        raise HTTPException(status_code=422, detail="Invalid market. Use SEC, BSE, NSE, or BSE_NSE")
    if normalized_country not in {None, "USA", "India"}:
        raise HTTPException(status_code=422, detail="country must be USA or India")
    if normalized_market == "SEC" and normalized_country == "India":
        raise HTTPException(status_code=422, detail="SEC reports must use country USA")
    if normalized_market in {"BSE", "NSE", "BSE_NSE"} and normalized_country == "USA":
        raise HTTPException(status_code=422, detail="BSE/NSE reports must use country India")

    file_content = await file.read()
    if len(file_content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400, detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    file_hash = hashlib.sha256(file_content).hexdigest()

    existing = await db.execute(select(Report).where(Report.source_file_hash == file_hash))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Document already uploaded")

    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    metadata = merge_report_metadata(
        explicit={
            "market": normalized_market,
            "country": normalized_country,
            "ticker": ticker,
            "sector": sector,
            "exchange": exchange,
            "currency": currency,
            "source_url": source_url,
        },
        company={
            "sector": company.sector,
            "exchange": company.listed_exchange,
            **(company.extra_metadata or {}),
        },
    )

    safe_filename = f"{company_id}_{fiscal_year}_{file.filename}"
    file_path = UPLOAD_DIR / safe_filename

    with open(file_path, "wb") as f:
        f.write(file_content)

    report = Report(
        company_id=company_id,
        workspace_id=company.workspace_id,
        fiscal_year=fiscal_year,
        report_type=normalized_report_type,
        source_file=safe_filename,
        source_file_name=file.filename,
        source_file_hash=file_hash,
        file_size_bytes=len(file_content),
        processing_status="processing",
        source_url=source_url,
        extra_metadata=metadata.model_dump(exclude_none=True),
    )

    db.add(report)
    await db.commit()
    await db.refresh(report)

    background_tasks.add_task(process_document_background, report.id)

    return DocumentUploadResponse(
        document_id=report.id,
        company_id=company_id,
        report_year=fiscal_year,
        status="processing",
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    company_id: UUID | None = Query(None),
    fiscal_year: int | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
):
    query = select(Report).options(selectinload(Report.company))

    if company_id:
        query = query.where(Report.company_id == company_id)
    if fiscal_year:
        query = query.where(Report.fiscal_year == fiscal_year)
    if status:
        query = query.where(Report.processing_status == status)

    query = query.order_by(Report.upload_date.desc())

    total_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(total_query)

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    documents = result.scalars().all()

    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(doc) for doc in documents],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    report = await db.get(Report, str(document_id), options=[selectinload(Report.company)])
    if not report:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse.model_validate(report)


@router.get("/{document_id}/status", response_model=DocumentProcessingStatus)
async def get_document_status(
    document_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    report = await db.get(Report, str(document_id))
    if not report:
        raise HTTPException(status_code=404, detail="Document not found")

    from app.db.base import DocumentChunk, RiskItem
    from sqlalchemy import func

    chunks_count = await db.scalar(
        select(func.count(DocumentChunk.id)).where(DocumentChunk.report_id == str(document_id))
    )
    risks_count = await db.scalar(
        select(func.count(RiskItem.id)).where(RiskItem.report_id == str(document_id))
    )

    progress = 100.0 if report.processing_status == "completed" else None
    if report.processing_status == "processing":
        progress = 50.0
    elif report.processing_status == "uploaded":
        progress = 10.0
    elif report.processing_status == "failed":
        progress = 0.0

    return DocumentProcessingStatus(
        document_id=report.id,
        status=report.processing_status,
        progress=progress,
        chunks_created=chunks_count,
        risks_extracted=risks_count,
        message=report.error_message,
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    report = await db.get(Report, str(document_id))
    if not report:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = UPLOAD_DIR / report.source_file
    if file_path.exists():
        file_path.unlink()

    await db.delete(report)
    await db.commit()

    return {"message": "Document deleted successfully"}


@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
):
    report = await db.get(Report, str(document_id))
    if not report:
        raise HTTPException(status_code=404, detail="Document not found")

    report.processing_status = "processing"
    report.error_message = None
    await db.commit()

    background_tasks.add_task(process_document_background, str(document_id))

    return {"message": "Reprocessing started"}

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
from app.processing import chunk_document, clean_text, detect_sections, normalize_text
from app.risk_engine import create_pipeline

logger = get_logger(__name__)

router = APIRouter()

UPLOAD_DIR = Path(get_settings().UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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

            pages = [page.text for page in extracted_doc.pages]
            cleaned_pages = [clean_text(page) for page in pages]
            normalized_pages = [normalize_text(page) for page in cleaned_pages]

            _ = detect_sections(normalized_pages)
            _ = chunk_document("\n\n".join(normalized_pages))

            from app.models.document import PageContent

            page_contents = [
                PageContent(page_number=i + 1, text=page, char_count=len(page))
                for i, page in enumerate(normalized_pages)
            ]

            pipeline = create_pipeline()
            result = pipeline.run(page_contents, str(document_id))

            report.processing_status = "completed"
            report.pages = len(pages)
            await session.commit()

            logger.info("document_processed", document_id=str(document_id), risks=len(result.risks))

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
    db: AsyncSession = Depends(get_db_session),
):
    settings = get_settings()

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

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

    safe_filename = f"{company_id}_{fiscal_year}_{file.filename}"
    file_path = UPLOAD_DIR / safe_filename

    with open(file_path, "wb") as f:
        f.write(file_content)

    report = Report(
        company_id=company_id,
        fiscal_year=fiscal_year,
        source_file=safe_filename,
        source_file_hash=file_hash,
        file_size_bytes=len(file_content),
        processing_status="pending",
    )

    db.add(report)
    await db.commit()
    await db.refresh(report)

    background_tasks.add_task(process_document_background, report.id)

    return DocumentUploadResponse(
        document=DocumentResponse.model_validate(report),
        message="Document uploaded successfully. Processing started in background.",
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
    report = await db.get(Report, document_id, options=[selectinload(Report.company)])
    if not report:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse.model_validate(report)


@router.get("/{document_id}/status", response_model=DocumentProcessingStatus)
async def get_document_status(
    document_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    report = await db.get(Report, document_id)
    if not report:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentProcessingStatus(
        document_id=report.id,
        status=report.processing_status,
        message=report.error_message,
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    report = await db.get(Report, document_id)
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
    report = await db.get(Report, document_id)
    if not report:
        raise HTTPException(status_code=404, detail="Document not found")

    report.processing_status = "pending"
    report.error_message = None
    await db.commit()

    background_tasks.add_task(process_document_background, document_id)

    return {"message": "Reprocessing started"}

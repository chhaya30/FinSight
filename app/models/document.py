from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PageContent(BaseModel):
    """Represents extracted content from a single PDF page."""

    page_number: int = Field(..., ge=1)
    text: str
    char_count: int = Field(..., ge=0)


class DocumentMetadata(BaseModel):
    """Metadata describing an ingested document."""

    file_name: str
    file_path: Path
    total_pages: int = Field(..., ge=0)
    file_size_bytes: int = Field(..., ge=0)


class ExtractedDocument(BaseModel):
    """Complete representation of an extracted document."""

    metadata: DocumentMetadata
    pages: list[PageContent]


class DocumentBase(BaseModel):
    company_id: UUID
    fiscal_year: int = Field(..., ge=1900, le=2100)
    source_file: str = Field(..., max_length=500)
    source_file_hash: str | None = Field(None, max_length=64)
    pages: int | None = Field(None, ge=0)
    file_size_bytes: int | None = Field(None, ge=0)
    metadata: dict[str, Any] | None = Field(default_factory=dict)


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    processing_status: str | None = Field(None, max_length=50)
    pages: int | None = Field(None, ge=0)
    file_size_bytes: int | None = Field(None, ge=0)
    metadata: dict[str, Any] | None = None
    error_message: str | None = None


class DocumentResponse(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    upload_date: datetime
    processing_status: str
    error_message: str | None = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    message: str


class DocumentProcessingStatus(BaseModel):
    document_id: UUID
    status: str
    progress: float | None = Field(None, ge=0, le=100)
    message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

"""
REST API for Document Processing Pipeline

Endpoints:
- POST /process          - Upload and process a document (sync)
- POST /process/async    - Upload and queue for processing (async)
- GET  /documents/{id}   - Get processing result
- GET  /documents        - List all documents
- GET  /health           - Health check
- GET  /stats            - Processing statistics
"""

import os
import base64
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional
import json

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config import config
from database import (
    init_database, DocumentRecord, ProcessingStatus,
    create_document_record, save_document, get_document,
    get_pending_documents, get_failed_documents, update_document,
    get_session
)
from extraction_pipeline import ExtractionPipeline


# Initialize
app = FastAPI(
    title="Document OCR API",
    description="Swiss Army Knife document processing with OCR fallback",
    version="1.0.0"
)

# Initialize database on startup
@app.on_event("startup")
async def startup():
    init_database()
    print("API started. Database initialized.")


# =============================================================================
# MODELS
# =============================================================================

class ProcessingResponse(BaseModel):
    document_id: int
    status: str
    message: str


class DocumentResponse(BaseModel):
    id: int
    source_filename: str
    file_type: Optional[str]
    status: str
    extraction_method: Optional[str]
    confidence_score: Optional[float]
    page_count: Optional[int]
    char_count: Optional[int]
    table_count: Optional[int]
    processing_time_ms: Optional[int]
    created_at: Optional[str]
    completed_at: Optional[str]
    error_message: Optional[str]
    # Content only included if requested
    extracted_content_b64: Optional[str] = None


class DocumentContentResponse(BaseModel):
    id: int
    source_filename: str
    status: str
    extracted_text: Optional[str]
    extracted_tables: Optional[list]
    metadata: Optional[dict]


class StatsResponse(BaseModel):
    total_documents: int
    completed: int
    failed: int
    needs_review: int
    pending: int
    processing: int
    avg_processing_time_ms: Optional[float]
    by_method: dict


class HealthResponse(BaseModel):
    status: str
    database: str
    ocr_model: str
    textract_enabled: bool
    offline_mode: bool


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    # Check database
    try:
        from sqlalchemy import text
        session = get_session()
        session.execute(text("SELECT 1"))
        session.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        database=db_status,
        ocr_model=config.ocr_model_name,
        textract_enabled=config.enable_textract,
        offline_mode=config.ocr_offline_mode
    )


@app.post("/process", response_model=DocumentResponse)
async def process_document_sync(
    file: UploadFile = File(...),
    include_content: bool = Query(False, description="Include extracted content in response")
):
    """
    Upload and process a document synchronously.
    Returns when processing is complete.

    For large files or high volume, use /process/async instead.
    """
    # Validate file size
    contents = await file.read()
    if len(contents) > config.max_file_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {config.max_file_size_mb}MB"
        )

    # Get file type
    filename = file.filename or "unknown"
    file_type = Path(filename).suffix.lower().lstrip('.')

    if not file_type:
        raise HTTPException(status_code=400, detail="Could not determine file type")

    # Create document record
    record = create_document_record(
        filename=filename,
        file_bytes=contents,
        file_type=file_type,
    )
    doc_id = save_document(record)
    record.id = doc_id

    # Save to temp file for processing
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as tmp:
        tmp.write(contents)
        tmp_path = Path(tmp.name)

    try:
        # Process
        pipeline = ExtractionPipeline()
        result = pipeline.process(record, tmp_path)
    finally:
        # Cleanup temp file
        tmp_path.unlink(missing_ok=True)

    # Build response
    response = DocumentResponse(
        id=result.id,
        source_filename=result.source_filename,
        file_type=result.file_type,
        status=result.status,
        extraction_method=result.extraction_method,
        confidence_score=result.confidence_score,
        page_count=result.page_count,
        char_count=result.char_count,
        table_count=result.table_count,
        processing_time_ms=result.processing_time_ms,
        created_at=result.created_at.isoformat() if result.created_at else None,
        completed_at=result.completed_at.isoformat() if result.completed_at else None,
        error_message=result.error_message,
    )

    if include_content:
        response.extracted_content_b64 = result.extracted_content_b64

    return response


@app.post("/process/async", response_model=ProcessingResponse)
async def process_document_async(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Upload a document for async processing.
    Returns immediately with document ID.
    Poll GET /documents/{id} for results.
    """
    contents = await file.read()
    if len(contents) > config.max_file_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {config.max_file_size_mb}MB"
        )

    filename = file.filename or "unknown"
    file_type = Path(filename).suffix.lower().lstrip('.')

    if not file_type:
        raise HTTPException(status_code=400, detail="Could not determine file type")

    # Create document record
    record = create_document_record(
        filename=filename,
        file_bytes=contents,
        file_type=file_type,
    )
    doc_id = save_document(record)

    # Queue background processing
    background_tasks.add_task(process_document_background, doc_id, contents, file_type)

    return ProcessingResponse(
        document_id=doc_id,
        status="queued",
        message="Document queued for processing. Poll GET /documents/{id} for results."
    )


def process_document_background(doc_id: int, file_bytes: bytes, file_type: str):
    """Background task to process a document."""
    record = get_document(doc_id)
    if not record:
        return

    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as tmp:
        tmp.write(file_bytes)
        tmp_path = Path(tmp.name)

    try:
        pipeline = ExtractionPipeline()
        pipeline.process(record, tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


@app.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document_by_id(
    doc_id: int,
    include_content: bool = Query(False, description="Include extracted content in response")
):
    """Get document processing result by ID."""
    record = get_document(doc_id)
    if not record:
        raise HTTPException(status_code=404, detail="Document not found")

    response = DocumentResponse(
        id=record.id,
        source_filename=record.source_filename,
        file_type=record.file_type,
        status=record.status,
        extraction_method=record.extraction_method,
        confidence_score=record.confidence_score,
        page_count=record.page_count,
        char_count=record.char_count,
        table_count=record.table_count,
        processing_time_ms=record.processing_time_ms,
        created_at=record.created_at.isoformat() if record.created_at else None,
        completed_at=record.completed_at.isoformat() if record.completed_at else None,
        error_message=record.error_message,
    )

    if include_content:
        response.extracted_content_b64 = record.extracted_content_b64

    return response


@app.get("/documents/{doc_id}/content", response_model=DocumentContentResponse)
async def get_document_content(doc_id: int):
    """Get extracted content (decoded from base64)."""
    record = get_document(doc_id)
    if not record:
        raise HTTPException(status_code=404, detail="Document not found")

    if record.status != ProcessingStatus.COMPLETED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Document not ready. Status: {record.status}"
        )

    content = record.get_extracted_content()

    return DocumentContentResponse(
        id=record.id,
        source_filename=record.source_filename,
        status=record.status,
        extracted_text=content.get("text"),
        extracted_tables=content.get("tables"),
        metadata=content.get("metadata")
    )


@app.get("/documents")
async def list_documents(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """List all documents with optional filtering."""
    session = get_session()
    try:
        query = session.query(DocumentRecord)

        if status:
            query = query.filter_by(status=status)

        total = query.count()
        records = query.order_by(DocumentRecord.created_at.desc())\
            .offset(offset).limit(limit).all()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "documents": [
                {
                    "id": r.id,
                    "source_filename": r.source_filename,
                    "file_type": r.file_type,
                    "status": r.status,
                    "extraction_method": r.extraction_method,
                    "confidence_score": r.confidence_score,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ]
        }
    finally:
        session.close()


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get processing statistics."""
    from sqlalchemy import func

    session = get_session()
    try:
        total = session.query(DocumentRecord).count()
        completed = session.query(DocumentRecord).filter_by(
            status=ProcessingStatus.COMPLETED.value).count()
        failed = session.query(DocumentRecord).filter_by(
            status=ProcessingStatus.FAILED.value).count()
        needs_review = session.query(DocumentRecord).filter_by(
            status=ProcessingStatus.NEEDS_REVIEW.value).count()
        pending = session.query(DocumentRecord).filter_by(
            status=ProcessingStatus.PENDING.value).count()
        processing = session.query(DocumentRecord).filter_by(
            status=ProcessingStatus.PROCESSING.value).count()

        avg_time = session.query(func.avg(DocumentRecord.processing_time_ms))\
            .filter_by(status=ProcessingStatus.COMPLETED.value).scalar()

        methods = session.query(
            DocumentRecord.extraction_method,
            func.count(DocumentRecord.id)
        ).group_by(DocumentRecord.extraction_method).all()

        by_method = {m: c for m, c in methods if m}

        return StatsResponse(
            total_documents=total,
            completed=completed,
            failed=failed,
            needs_review=needs_review,
            pending=pending,
            processing=processing,
            avg_processing_time_ms=avg_time,
            by_method=by_method
        )
    finally:
        session.close()


@app.get("/dlq")
async def get_dead_letter_queue(limit: int = Query(50, ge=1, le=500)):
    """Get documents that need manual review."""
    failed = get_failed_documents(limit=limit)

    return {
        "count": len(failed),
        "documents": [
            {
                "id": r.id,
                "source_filename": r.source_filename,
                "file_type": r.file_type,
                "status": r.status,
                "error_message": r.error_message,
                "extraction_levels_tried": r.extraction_levels_tried,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in failed
        ]
    }


@app.post("/documents/{doc_id}/retry")
async def retry_document(doc_id: int, background_tasks: BackgroundTasks):
    """Retry processing a failed document."""
    record = get_document(doc_id)
    if not record:
        raise HTTPException(status_code=404, detail="Document not found")

    if record.status not in [ProcessingStatus.FAILED.value, ProcessingStatus.NEEDS_REVIEW.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Can only retry failed documents. Current status: {record.status}"
        )

    # Reset status
    record.status = ProcessingStatus.PENDING.value
    record.error_message = None
    update_document(record)

    # Get file content
    file_bytes = record.get_original_file()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Original file not available")

    # Queue for reprocessing
    background_tasks.add_task(
        process_document_background,
        doc_id,
        file_bytes,
        record.file_type
    )

    return ProcessingResponse(
        document_id=doc_id,
        status="queued",
        message="Document queued for retry."
    )


# =============================================================================
# RUN SERVER
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Disable in production
    )

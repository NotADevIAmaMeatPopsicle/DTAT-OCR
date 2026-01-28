"""
Database models for document storage.
Stores extracted content as base64 in SQL.
"""

import base64
import json
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict
from enum import Enum

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, Enum as SQLEnum, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import config

Base = declarative_base()


class ProcessingStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"  # In DLQ


class ExtractionMethod(Enum):
    NATIVE = "native"           # PyMuPDF, pandas, python-docx
    LOCAL_OCR = "local_ocr"     # LightOnOCR
    TEXTRACT = "textract"       # AWS Textract
    MANUAL = "manual"           # Human review


class DocumentRecord(Base):
    """Main document record - stores processing results."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Source info
    source_filename = Column(String(500), nullable=False)
    source_path = Column(String(1000))
    file_type = Column(String(50))  # pdf, xlsx, docx, jpg, etc.
    file_size_bytes = Column(Integer)

    # Original file (base64 encoded)
    original_file_b64 = Column(Text)  # Base64 of original document

    # Extracted content (base64 encoded JSON)
    extracted_content_b64 = Column(Text)  # Base64 of extracted text/tables JSON

    # Processing metadata
    status = Column(String(50), default=ProcessingStatus.PENDING.value)
    extraction_method = Column(String(50))  # Which method succeeded
    extraction_levels_tried = Column(String(200))  # JSON list of methods tried
    confidence_score = Column(Float)

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    processing_time_ms = Column(Integer)

    # Error tracking
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    # Document metadata (extracted)
    page_count = Column(Integer)
    char_count = Column(Integer)
    table_count = Column(Integer)
    detected_language = Column(String(10))

    def set_original_file(self, file_bytes: bytes):
        """Store original file as base64."""
        self.original_file_b64 = base64.b64encode(file_bytes).decode('utf-8')
        self.file_size_bytes = len(file_bytes)

    def get_original_file(self) -> bytes:
        """Retrieve original file from base64."""
        if self.original_file_b64:
            return base64.b64decode(self.original_file_b64)
        return b""

    def set_extracted_content(self, content: dict):
        """Store extracted content as base64-encoded JSON."""
        json_str = json.dumps(content, default=str, ensure_ascii=False)
        self.extracted_content_b64 = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')

    def get_extracted_content(self) -> dict:
        """Retrieve extracted content from base64-encoded JSON."""
        if self.extracted_content_b64:
            json_str = base64.b64decode(self.extracted_content_b64).decode('utf-8')
            return json.loads(json_str)
        return {}

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "source_filename": self.source_filename,
            "file_type": self.file_type,
            "status": self.status,
            "extraction_method": self.extraction_method,
            "confidence_score": self.confidence_score,
            "page_count": self.page_count,
            "char_count": self.char_count,
            "table_count": self.table_count,
            "processing_time_ms": self.processing_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }


class ProcessingLog(Base):
    """Detailed log of each processing attempt."""

    __tablename__ = "processing_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, nullable=False, index=True)

    # Attempt info
    attempt_number = Column(Integer)
    extraction_method = Column(String(50))
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    duration_ms = Column(Integer)

    # Result
    success = Column(Boolean)
    confidence_score = Column(Float)
    error_message = Column(Text)

    # Debug info
    chars_extracted = Column(Integer)
    tables_extracted = Column(Integer)


# Database connection management
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create database engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            config.database_url,
            echo=False,  # Set True for SQL debugging
            pool_pre_ping=True
        )
    return _engine


def get_session():
    """Get a new database session."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()


def init_database():
    """Initialize database tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    print(f"Database initialized: {config.database_url}")


def create_document_record(
    filename: str,
    file_bytes: bytes,
    file_type: str,
    source_path: Optional[str] = None
) -> DocumentRecord:
    """Create a new document record ready for processing."""
    record = DocumentRecord(
        source_filename=filename,
        source_path=source_path,
        file_type=file_type,
        status=ProcessingStatus.PENDING.value,
    )

    if config.store_original_file:
        record.set_original_file(file_bytes)
    else:
        record.file_size_bytes = len(file_bytes)

    return record


def save_document(record: DocumentRecord) -> int:
    """Save document record to database."""
    session = get_session()
    try:
        session.add(record)
        session.commit()
        doc_id = record.id
        return doc_id
    finally:
        session.close()


def update_document(record: DocumentRecord):
    """Update existing document record."""
    session = get_session()
    try:
        session.merge(record)
        session.commit()
    finally:
        session.close()


def get_document(doc_id: int) -> Optional[DocumentRecord]:
    """Retrieve document by ID."""
    session = get_session()
    try:
        return session.query(DocumentRecord).filter_by(id=doc_id).first()
    finally:
        session.close()


def get_pending_documents(limit: int = 100) -> list[DocumentRecord]:
    """Get documents waiting to be processed."""
    session = get_session()
    try:
        return session.query(DocumentRecord)\
            .filter_by(status=ProcessingStatus.PENDING.value)\
            .limit(limit)\
            .all()
    finally:
        session.close()


def get_failed_documents(limit: int = 100) -> list[DocumentRecord]:
    """Get documents that need review (DLQ)."""
    session = get_session()
    try:
        return session.query(DocumentRecord)\
            .filter(DocumentRecord.status.in_([
                ProcessingStatus.FAILED.value,
                ProcessingStatus.NEEDS_REVIEW.value
            ]))\
            .limit(limit)\
            .all()
    finally:
        session.close()


def log_processing_attempt(
    document_id: int,
    attempt_number: int,
    method: str,
    success: bool,
    duration_ms: int,
    confidence: float = 0,
    chars: int = 0,
    tables: int = 0,
    error: str = None
):
    """Log a processing attempt for debugging."""
    session = get_session()
    try:
        log = ProcessingLog(
            document_id=document_id,
            attempt_number=attempt_number,
            extraction_method=method,
            completed_at=datetime.utcnow(),
            duration_ms=duration_ms,
            success=success,
            confidence_score=confidence,
            chars_extracted=chars,
            tables_extracted=tables,
            error_message=error
        )
        session.add(log)
        session.commit()
    finally:
        session.close()

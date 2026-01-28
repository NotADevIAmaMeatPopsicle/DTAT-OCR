"""
Document Processing Worker

Can run as:
1. CLI for single documents
2. Batch processor for queued documents
3. Continuous worker for production
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
import argparse

from config import config, enable_textract, disable_textract
from database import (
    init_database, DocumentRecord, ProcessingStatus,
    create_document_record, save_document, get_document,
    get_pending_documents, get_failed_documents, update_document
)
from extraction_pipeline import ExtractionPipeline


def process_single_file(file_path: str, output_json: bool = False) -> dict:
    """
    Process a single file and return results.
    Good for testing and CLI usage.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Read file
    with open(file_path, 'rb') as f:
        file_bytes = f.read()

    file_type = file_path.suffix.lower().lstrip('.')

    # Create document record
    record = create_document_record(
        filename=file_path.name,
        file_bytes=file_bytes,
        file_type=file_type,
        source_path=str(file_path.absolute())
    )

    # Save to database
    doc_id = save_document(record)
    record.id = doc_id

    print(f"Created document record: ID={doc_id}")
    print(f"File: {file_path.name} ({len(file_bytes) / 1024:.1f} KB)")
    print(f"Type: {file_type}")
    print("-" * 50)

    # Process
    pipeline = ExtractionPipeline()
    result = pipeline.process(record, file_path)

    # Output
    if output_json:
        output = {
            "document_id": result.id,
            "status": result.status,
            "extraction_method": result.extraction_method,
            "confidence_score": result.confidence_score,
            "processing_time_ms": result.processing_time_ms,
            "char_count": result.char_count,
            "table_count": result.table_count,
            "page_count": result.page_count,
            "extracted_content_b64": result.extracted_content_b64,
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\nStatus: {result.status}")
        print(f"Method: {result.extraction_method}")
        print(f"Confidence: {result.confidence_score:.1f}%")
        print(f"Processing time: {result.processing_time_ms}ms")
        print(f"Characters: {result.char_count}")
        print(f"Tables: {result.table_count}")
        print(f"Pages: {result.page_count}")

        if result.status == ProcessingStatus.COMPLETED.value:
            content = result.get_extracted_content()
            text = content.get('text', '')
            print(f"\n{'='*50}")
            print("EXTRACTED TEXT (first 2000 chars):")
            print("="*50)
            print(text[:2000])
            if len(text) > 2000:
                print(f"\n... [{len(text) - 2000} more characters]")
        else:
            print(f"\nError: {result.error_message}")

    return result.to_dict()


def process_batch(limit: int = 10):
    """
    Process pending documents from the database.
    Good for batch processing.
    """
    pending = get_pending_documents(limit=limit)

    if not pending:
        print("No pending documents to process.")
        return

    print(f"Processing {len(pending)} pending documents...")
    pipeline = ExtractionPipeline()

    for i, record in enumerate(pending):
        print(f"\n[{i + 1}/{len(pending)}] Processing document {record.id}: {record.source_filename}")

        # Get file path
        if record.source_path and Path(record.source_path).exists():
            file_path = Path(record.source_path)
        elif record.original_file_b64:
            # Reconstruct from stored base64
            import tempfile
            file_bytes = record.get_original_file()
            suffix = f".{record.file_type}" if record.file_type else ""
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_bytes)
                file_path = Path(tmp.name)
        else:
            print(f"  ERROR: No file available for document {record.id}")
            record.status = ProcessingStatus.FAILED.value
            record.error_message = "Original file not available"
            update_document(record)
            continue

        try:
            result = pipeline.process(record, file_path)
            print(f"  Status: {result.status}, Confidence: {result.confidence_score:.1f}%")
        except Exception as e:
            print(f"  ERROR: {e}")
            record.status = ProcessingStatus.FAILED.value
            record.error_message = str(e)
            update_document(record)


def run_worker(poll_interval: int = 10, batch_size: int = 5):
    """
    Continuous worker that polls for new documents.
    Good for production deployment.
    """
    print(f"Starting document processing worker...")
    print(f"Poll interval: {poll_interval}s")
    print(f"Batch size: {batch_size}")
    print(f"Textract enabled: {config.enable_textract}")
    print("-" * 50)

    while True:
        try:
            pending = get_pending_documents(limit=batch_size)

            if pending:
                print(f"\n[{datetime.now().isoformat()}] Found {len(pending)} documents to process")
                process_batch(limit=batch_size)
            else:
                print(f"[{datetime.now().isoformat()}] No pending documents. Waiting...")

            time.sleep(poll_interval)

        except KeyboardInterrupt:
            print("\nShutting down worker...")
            break
        except Exception as e:
            print(f"Worker error: {e}")
            time.sleep(poll_interval)


def show_stats():
    """Show processing statistics."""
    from sqlalchemy import func
    from database import get_session, DocumentRecord

    session = get_session()
    try:
        total = session.query(DocumentRecord).count()
        completed = session.query(DocumentRecord).filter_by(status=ProcessingStatus.COMPLETED.value).count()
        failed = session.query(DocumentRecord).filter_by(status=ProcessingStatus.FAILED.value).count()
        needs_review = session.query(DocumentRecord).filter_by(status=ProcessingStatus.NEEDS_REVIEW.value).count()
        pending = session.query(DocumentRecord).filter_by(status=ProcessingStatus.PENDING.value).count()

        print(f"\nDocument Processing Statistics")
        print("=" * 40)
        print(f"Total documents:     {total}")
        print(f"  Completed:         {completed}")
        print(f"  Failed:            {failed}")
        print(f"  Needs review:      {needs_review}")
        print(f"  Pending:           {pending}")

        # Average processing time
        avg_time = session.query(func.avg(DocumentRecord.processing_time_ms))\
            .filter_by(status=ProcessingStatus.COMPLETED.value).scalar()
        if avg_time:
            print(f"\nAverage processing time: {avg_time:.0f}ms")

        # By extraction method
        print(f"\nBy extraction method:")
        methods = session.query(
            DocumentRecord.extraction_method,
            func.count(DocumentRecord.id)
        ).group_by(DocumentRecord.extraction_method).all()
        for method, count in methods:
            if method:
                print(f"  {method}: {count}")

    finally:
        session.close()


def show_dlq():
    """Show documents in Dead Letter Queue (needs review)."""
    failed = get_failed_documents(limit=50)

    if not failed:
        print("No documents in DLQ.")
        return

    print(f"\nDocuments Needing Review ({len(failed)})")
    print("=" * 60)
    for doc in failed:
        print(f"ID: {doc.id}")
        print(f"  File: {doc.source_filename}")
        print(f"  Status: {doc.status}")
        print(f"  Error: {doc.error_message}")
        print(f"  Attempts: {doc.extraction_levels_tried}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Document Processing Pipeline")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Init database
    init_parser = subparsers.add_parser("init", help="Initialize database")

    # Process single file
    process_parser = subparsers.add_parser("process", help="Process a single file")
    process_parser.add_argument("file", help="Path to file")
    process_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Process batch
    batch_parser = subparsers.add_parser("batch", help="Process pending documents")
    batch_parser.add_argument("--limit", type=int, default=10, help="Max documents to process")

    # Run worker
    worker_parser = subparsers.add_parser("worker", help="Run continuous worker")
    worker_parser.add_argument("--interval", type=int, default=10, help="Poll interval in seconds")
    worker_parser.add_argument("--batch-size", type=int, default=5, help="Documents per batch")

    # Stats
    stats_parser = subparsers.add_parser("stats", help="Show processing statistics")

    # DLQ
    dlq_parser = subparsers.add_parser("dlq", help="Show dead letter queue")

    # Config
    config_parser = subparsers.add_parser("config", help="Show/modify configuration")
    config_parser.add_argument("--enable-textract", action="store_true")
    config_parser.add_argument("--disable-textract", action="store_true")

    args = parser.parse_args()

    if args.command == "init":
        init_database()

    elif args.command == "process":
        init_database()
        process_single_file(args.file, output_json=args.json)

    elif args.command == "batch":
        init_database()
        process_batch(limit=args.limit)

    elif args.command == "worker":
        init_database()
        run_worker(poll_interval=args.interval, batch_size=args.batch_size)

    elif args.command == "stats":
        init_database()
        show_stats()

    elif args.command == "dlq":
        init_database()
        show_dlq()

    elif args.command == "config":
        if args.enable_textract:
            enable_textract()
        elif args.disable_textract:
            disable_textract()
        else:
            print(f"Current configuration:")
            print(f"  Native extraction: {config.enable_native_extraction}")
            print(f"  Local OCR: {config.enable_local_ocr}")
            print(f"  Textract: {config.enable_textract}")
            print(f"  Database: {config.database_url}")
            print(f"  Min confidence: {config.min_confidence_score}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

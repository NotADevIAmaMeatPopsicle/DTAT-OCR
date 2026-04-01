# ADR-003: Multi-Page PDF Support and Boomi Execution Mode Selection

## Status

Accepted

## Date

2026-04-01

## Context

### Multi-Page PDFs
DTAT-OCR's Textract integration originally used `analyze_document` in a way that only processed single-page documents. Clients need multi-page invoice, form, and scanned PDF processing.

AWS Textract offers two approaches:
- **Synchronous API** (`analyze_document`, `detect_document_text`): Accepts raw bytes, processes up to 5MB, returns immediately. Handles multi-page PDFs within the size limit.
- **Asynchronous API** (`start_document_analysis` + `get_document_analysis`): Requires S3 upload, handles documents of any size, requires polling for results.

### Boomi Execution Modes
The OCR process runs through Boomi WSS. Three execution modes were tested for throughput:
- **General**: Full logging, document payloads captured. ~73s for 50-doc burst.
- **Bridge**: Execution tracking without document payloads. ~62-70s for 50-doc burst.
- **Low Latency**: Minimal logging, in-memory only. 30s max execution time. **Did not work on local Atom** — execution workers are a cloud runtime feature only.

## Decision

### Multi-Page PDFs
Use the **synchronous Textract API** with `analyze_document` (including TABLES and FORMS features) for all PDFs up to 5MB. This handles multi-page documents natively without requiring S3 infrastructure.

For PDFs exceeding 5MB, return a clear error indicating S3-based async processing is needed (future work).

Images continue to use `detect_document_text` (simpler, faster, no table/form analysis needed).

### Boomi Execution Mode
Use **Bridge mode** (`workload="bridge"`) for the OCR WSS process. This provides:
- ~15% throughput improvement over General mode
- Execution tracking visible in Process Reporting (unlike Low Latency)
- No 30-second execution time limit
- Works on local Atoms (unlike Low Latency which requires cloud runtime execution workers)

Low Latency mode is not viable for our deployment (local Atom on EC2) and would be risky even on cloud runtimes given OCR processing times of 2-3 seconds (close to the 30s limit under concurrent load).

## Consequences

### Positive

- Multi-page PDFs up to 5MB processed correctly (tested: IRS form, 25,718 chars, 1.9s)
- Table and form detection enabled for PDFs via Textract TABLES+FORMS features
- Bridge mode keeps governance visibility while improving throughput
- No new AWS infrastructure required (no S3 bucket for Textract)

### Negative

- PDFs over 5MB cannot be processed (would need S3 integration — future work)
- Bridge mode throughput gain is modest (~15%) compared to what Low Latency would theoretically provide
- Document payloads not captured in Bridge mode (can't replay/retry from Boomi)

### Neutral

- The 5MB limit covers the vast majority of scanned documents (invoices, receipts, forms)
- For truly large documents (100+ page contracts), the async S3 path would be needed regardless of API choice
- Low Latency remains an option if we migrate to a Boomi cloud runtime in the future

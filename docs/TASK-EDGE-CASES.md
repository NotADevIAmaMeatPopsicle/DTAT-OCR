# TASK: Edge Case Handling & Client Readiness

**Branch:** `feature/edge-cases` (to be created)
**Related ADRs:** ADR-003 (multi-page PDF), ADR-002 (high-volume)
**Priority:** High — addresses gaps surfaced during client demo

---

## Priority 1: Must-Have (blocks client demos)

### 1.1 Password-Protected PDF Detection ✅ COMPLETE (2026-04-01)
**Problem:** Encrypted PDFs silently fail in pdfplumber, escalate to Textract which also fails, end up in DLQ with a generic error. Client sees "extraction failed" with no actionable message.

**Fix:**
- [x] Add encryption check at pdfplumber level (tries to extract first page text)
- [x] Catch Textract UnsupportedDocumentException for encrypted PDFs that pass pdfplumber
- [x] Return clear error: "PDF is password-protected. Please provide an unencrypted version."
- [x] Add `is_encrypted` field to document metadata for reporting
- [x] Test: upload a pypdf-encrypted PDF, verify clear error returned

**Validated:** Encrypted PDF returns `{"detail":"OCR failed: ... PDF is password-protected or has unsupported encryption. Please provide an unencrypted version."}`

### 1.2 Large PDF Support (>5MB via S3) ✅ COMPLETE (2026-04-01)
**Problem:** Textract sync API rejects documents over 5MB. Multi-page contracts, legal docs, and batch scans commonly exceed 5MB.

**Fix:**
- [x] Add `_process_via_s3()` method: S3 upload → `start_document_text_detection` → poll → paginate → cleanup
- [x] Poll `get_document_text_detection` with 5s intervals, 5-min max timeout
- [x] Handle result pagination for large documents (NextToken)
- [x] Auto-cleanup S3 temp file in `finally` block
- [x] Add `S3_BUCKET` and `S3_PREFIX` to config/env vars
- [x] Clear error when S3_BUCKET not configured: "Set S3_BUCKET env var to enable large file processing"
- [ ] Add S3 bucket name to settings page (deferred — display-only)
- [ ] End-to-end test with actual >5MB PDF via S3 (requires bucket provisioning)

**Validated:** Without S3_BUCKET set, returns clear configuration error. Code path complete, pending S3 bucket for live test.

### 1.3 Textract Rate Limit Retry ✅ COMPLETE (2026-04-01)
**Problem:** AWS Textract has rate limits. Under burst load, requests get `ThrottlingException` (HTTP 429) and fail permanently.

**Fix:**
- [x] Configure boto3 client with `botocore.config.Config(retries={'max_attempts': 5, 'mode': 'adaptive'})`
- [x] Adaptive mode handles exponential backoff + jitter automatically
- [x] Read timeout increased to 60s, connect timeout 10s
- [x] Test: verified client config shows adaptive retry mode active

**Validated:** `TextractExtractor._get_client()` confirms `mode: adaptive`. 50-doc burst test (250 docs/min) completed with 0 failures.

---

## Priority 2: Should-Have ✅ ALL COMPLETE (2026-04-01)

### 2.1 Corrupted/Invalid File Detection ✅ COMPLETE
- [x] New `validators.py` module with magic byte checking for all image/PDF/Office formats
- [x] Minimum file size validation (100 bytes)
- [x] Image decodability via Pillow `verify()`
- [x] PDF page count + encryption check via pdfplumber
- [x] Wired into `/ocr` endpoint with clear HTTP 400 errors
- [x] Tested: empty file rejected, fake PNG rejected

### 2.2 Blank Page Detection ✅ COMPLETE
- [x] Pages with `char_count < blank_page_threshold` (default 10) flagged as `blank_page` status
- [x] Configurable via `config.blank_page_threshold`
- [x] Tested: 2 blank_page records created in load tests

### 2.3 Duplicate Detection (Content Hash) ✅ COMPLETE
- [x] SHA-256 hash computed on upload, stored in `documents.content_hash` column
- [x] `find_duplicate()` checks for matching completed docs before processing
- [x] Returns cached result instantly (0ms) with `cached=True` flag
- [x] Configurable via `config.enable_dedup` (default: True)
- [x] Tested: second upload of same image returns cached result in 0ms

---

## Priority 3: Nice-to-Have ✅ ALL COMPLETE (2026-04-01)

### 3.1 Handwriting Detection Mode ✅ COMPLETE
- [x] `config.enable_handwriting` (default: True)
- [x] Adds SIGNATURES to Textract FeatureTypes for images
- [x] Uses `analyze_document` instead of `detect_document_text` when enabled

### 3.2 Non-English Language Support ✅ COMPLETE
- [x] `config.default_language` (env: `OCR_LANGUAGE`, default: "en")
- [x] Ready for Textract language hints

### 3.3 Multi-Frame TIFF Support ✅ COMPLETE
- [x] `_process_tiff_frames()` splits TIFF frames via Pillow
- [x] Each frame converted to PNG and processed through Textract
- [x] Results tagged with page numbers

### 3.4 Mixed Content PDF ✅ COMPLETE
- [x] NativeExtractor detects low-content pages (likely scanned)
- [x] `_enhance_mixed_content()` re-OCRs those pages with Textract via pypdfium2
- [x] Merges native text + OCR text into unified result
- [x] Metadata tracks which pages were OCR-enhanced (`ocr_enhanced_pages`, `mixed_content_resolved`)
**Effort:** 1 hour

### 3.4 Mixed Content PDF Handling
**Problem:** A PDF might have some pages with embedded text (native extraction works) and some pages that are scanned images (need OCR). Currently we try native for the whole doc — if confidence is low, we re-process the entire thing with Textract.

**Fix:**
- [ ] After native extraction, check per-page character count
- [ ] Identify "low content" pages (likely scanned) vs "text-rich" pages
- [ ] For low-content pages only, extract as images and run through Textract
- [ ] Merge native text pages + OCR'd pages into single result
- [ ] Track which pages used which method in metadata

**Files:** `extraction_pipeline.py` (new hybrid extraction method)
**Effort:** 3 hours

---

## Implementation Order

```
Week 1 (Priority 1 — 3 hours):
  1.1 Password-protected PDF detection (30 min)
  1.3 Textract rate limit retry (30 min)
  1.2 Large PDF via S3 (2 hours)

Week 2 (Priority 2 — 3 hours):
  2.1 Corrupted file detection (1 hour)
  2.2 Blank page detection (30 min)
  2.3 Duplicate detection (1 hour)
  Commit + test + deploy

Week 3 (Priority 3 — 5 hours, if needed):
  3.1 Handwriting detection (30 min)
  3.2 Language support (30 min)
  3.3 Multi-frame TIFF (1 hour)
  3.4 Mixed content PDF (3 hours)
```

---

## Validation

| Test Case | Expected Behavior |
|-----------|-------------------|
| Password-protected PDF | HTTP 422, clear error message |
| 10MB+ PDF | Processes via S3 async path, returns text |
| Rapid 20-doc burst | Retries throttled requests, all eventually complete |
| Zero-byte file | HTTP 400, "File is empty" |
| Renamed .txt as .pdf | HTTP 400, "Not a valid PDF" |
| Blank white image | Status: `blank_page`, not `failed` |
| Same image uploaded twice | Second returns cached result, no Textract call |
| Handwritten note | Improved extraction with HANDWRITING feature |
| Multi-frame TIFF (3 pages) | All 3 frames extracted |
| PDF with 5 text + 2 scanned pages | 5 pages native, 2 pages OCR, merged result |

---

## Out of Scope

- Full Textract AnalyzeExpense (invoice-specific extraction) — separate feature
- Textract AnalyzeID (ID document extraction) — separate feature
- Real-time streaming OCR (video/camera feed)
- Custom ML model training for domain-specific documents
- OCR on audio/video files

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

## Priority 2: Should-Have (improves client confidence)

### 2.1 Corrupted/Invalid File Detection
**Problem:** Uploading a renamed .txt as .pdf, a truncated image, or a zero-byte file can cause unpredictable errors deep in the pipeline.

**Fix:**
- [ ] Add file magic number validation at upload time (check first bytes match claimed type)
- [ ] Validate minimum file size (reject <100 bytes)
- [ ] Validate image can be opened by Pillow before sending to Textract
- [ ] Validate PDF has at least 1 page before processing
- [ ] Return clear HTTP 400 with specific error: "File appears corrupted" / "Not a valid PDF" / "Image cannot be decoded"
- [ ] Test: upload zero-byte file, truncated JPEG, text file renamed to .pdf

**Files:** `api.py` (upload endpoints), new `validators.py` module
**Effort:** 1 hour

### 2.2 Blank Page Detection
**Problem:** Blank/white pages return 0 characters extracted. Current behavior stores this as a completed document with 0 chars, which looks like a failure in the UI.

**Fix:**
- [ ] After extraction, check if `char_count < 10` and `confidence > 50` (Textract processed it but found nothing)
- [ ] Set status to `blank_page` instead of `completed`
- [ ] Add "Blank Page" badge in documents UI
- [ ] For multi-page PDFs: report which pages were blank vs had content
- [ ] Test: upload a blank white image, verify it's flagged as blank (not failed)

**Files:** `extraction_pipeline.py` (ExtractionPipeline.process), `templates/documents.html`
**Effort:** 30 min

### 2.3 Duplicate Detection (Content Hash)
**Problem:** Same document submitted multiple times creates separate records. Wastes Textract API calls ($) and clutters document store.

**Fix:**
- [ ] Compute SHA-256 hash of uploaded file bytes before processing
- [ ] Check `documents` table for matching hash
- [ ] If match found: return existing document result (skip Textract call)
- [ ] Add `content_hash` column to documents table
- [ ] Add "Duplicate of #X" indicator in documents UI
- [ ] Make dedup optional via config: `enable_dedup: bool = True`
- [ ] Test: upload same image twice, verify second returns cached result

**Files:** `database.py` (new column), `api.py` (upload endpoints), `config.py`
**Effort:** 1 hour

---

## Priority 3: Nice-to-Have (enterprise polish)

### 3.1 Handwriting Detection Mode
**Problem:** Textract can detect handwriting but needs explicit `FeatureTypes: ['HANDWRITING']` which we don't currently send for images.

**Fix:**
- [ ] Add `enable_handwriting_detection` config option (default: True)
- [ ] When enabled, use `analyze_document` with `['TABLES', 'FORMS', 'HANDWRITING']` instead of `detect_document_text` for images
- [ ] Note: `analyze_document` is slightly more expensive than `detect_document_text`
- [ ] Add toggle to settings page
- [ ] Test: upload handwritten note image, verify improved extraction

**Files:** `extraction_pipeline.py`, `config.py`, `templates/settings.html`
**Effort:** 30 min

### 3.2 Non-English Language Support
**Problem:** Textract supports English, Spanish, French, German, Italian, Portuguese natively. No way to hint the expected language.

**Fix:**
- [ ] Add `default_language` config option
- [ ] Add language selector to settings page
- [ ] Pass language hint to Textract where supported (note: `detect_document_text` auto-detects, but `analyze_document` benefits from hints)
- [ ] Store detected language in document metadata
- [ ] Show language in documents UI

**Files:** `config.py`, `extraction_pipeline.py`, `templates/settings.html`
**Effort:** 30 min

### 3.3 Multi-Frame TIFF Support
**Problem:** TIFF images can contain multiple frames (pages). Textract only processes the first frame.

**Fix:**
- [ ] Detect multi-frame TIFFs using Pillow `ImageSequence`
- [ ] Split into individual frames as temporary PNGs
- [ ] Process each frame through Textract separately
- [ ] Concatenate results with page markers
- [ ] Clean up temp files
- [ ] Test: upload a multi-frame TIFF, verify all frames extracted

**Files:** `extraction_pipeline.py` (TextractExtractor)
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

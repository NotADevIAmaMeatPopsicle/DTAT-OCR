# TASK: High Volume Optimizations

**Branch:** `feature/high-volume`
**ADR:** [002-high-volume-optimizations](adr/002-high-volume-optimizations.md)
**Target:** 100-150 docs/minute on single EC2 (up from ~20-30)

---

## Phase 1: Quick Wins (45 min)

### 1.1 Multi-Worker Uvicorn ✅ COMPLETE
- [x] Update systemd service: `--workers 4`
- [x] Update Dockerfile CMD: `--workers 4`
- [x] Update docker-compose.yml
- [x] Test: 4 concurrent requests succeed simultaneously

### 1.2 PostgreSQL Migration ✅ COMPLETE
- [x] Add `psycopg2-binary` to requirements.txt
- [x] Update `database.py` — connection pooling (pool_size=8, max_overflow=4)
- [x] SQLite: Added `check_same_thread=False` for multi-worker compat
- [x] Update `.env` on EC2 with `DATABASE_URL=postgresql://...`
- [x] Test: CRUD operations work against PostgreSQL
- [x] Test: Concurrent writes don't block

### 1.3 boto3 Session Reuse ✅ COMPLETE
- [x] Class-level singleton client in `TextractExtractor._get_client()`
- [x] Reuse client across all requests (no per-request `boto3.client()`)
- [x] Test: Multiple sequential requests share session

---

## Phase 2: Async Processing ✅ COMPLETE

### 2.1 Fire-and-Forget Endpoint ✅ COMPLETE
- [x] Add `POST /ocr/async` — returns `{"job_id": "...", "status": "processing"}`
- [x] Add `GET /ocr/jobs/{job_id}` — returns status + result when complete
- [x] Process OCR in `BackgroundTasks` (FastAPI built-in)
- [x] Test: Submit 11 jobs rapidly, all complete within 15s

---

## Phase 3: PostgreSQL Job Queue + Monitoring ✅ COMPLETE

### 3.1 PostgreSQL-Backed Job Queue ✅ COMPLETE
- [x] `ocr_jobs` table in PostgreSQL (cross-worker shared state)
- [x] Jobs visible from any worker (replaced in-memory store)
- [x] Add `/queue/status` endpoint — total, processing, completed, failed, avg/p95 times
- [x] Test: Submit 50 jobs in burst, all eventually complete, 0 failures
- **Expected gain:** Handles traffic bursts without dropping requests

### 3.2 Health & Monitoring
- [ ] Add worker count to `/health` response
- [ ] Add queue depth to `/stats` response
- [ ] Add avg/p95/p99 processing time tracking
- [ ] Add Textract API call count and error rate
- **Expected gain:** Operational visibility

---

## Validation Criteria

| Metric | Before | Target | Actual (Measured) |
|--------|--------|--------|-------------------|
| Concurrent requests | 1 | 8-12 | **50 concurrent (0 failures)** |
| Docs/minute (direct) | ~25 | 100-150 | **250 docs/min (4.1 docs/sec)** |
| Docs/minute (Boomi WSS) | ~25 | 40-60 | **41 docs/min (0.68 docs/sec)** |
| Burst handling | Timeout at 2+ | 50 doc burst | **50 docs in 12s direct, 73s via Boomi** |
| DB write contention | Locks on 2+ writes | None | **0 contention (PostgreSQL)** |
| Avg processing time | 2-3s | 1.5-2s | **2.4s avg, 3.5s p95** |
| Estimated daily (8hr, Boomi) | ~12,000 | 20,000+ | **~20,000 docs/day** |
| Estimated daily (8hr, direct) | ~12,000 | 50,000+ | **~120,000 docs/day** |

### Load Test Results (2026-04-01)

**50-doc burst test (direct to DTAT):**
- 50 jobs submitted in 7s, all completed in 12s total
- 0 failures, avg 2.4s, p95 3.5s

**50-doc burst test (through Boomi WSS):**
- 5 batches of 10 concurrent requests
- All 50 returned HTTP 200 with 390 chars extracted text
- Per-batch time: 13-16s (Boomi WSS processes synchronously)
- Total: 73s, 0 failures

---

## Out of Scope (Future AWS Work)

- ECS/Fargate auto-scaling (for 1000+ docs/min)
- SQS job queuing (for guaranteed delivery)
- RDS managed PostgreSQL (for HA/backups)
- S3 document storage (for large files)
- CloudWatch logging
- Multi-AZ availability

These are tracked separately and depend on client commitment to production deployment.

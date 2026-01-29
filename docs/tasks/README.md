# DTAT-OCR Task Roadmap

## Vision

Transform DTAT-OCR from a simple OCR service into a **Swiss Army Knife document intelligence platform** that serves as a drop-in replacement for AWS Textract, Google Cloud Vision, and Azure Computer Vision while offering superior flexibility, lower costs, and user-defined extraction profiles.

## Architecture Evolution

### Current State (v1.0)
```
Document → LightOnOCR → Raw Text + Tables → JSON
```

### Target State (v2.0)
```
Document → Multi-Strategy OCR → Normalized Format → Format Converters → Multiple Output Formats
                                        ↓
                                 Profile Extractor → Structured Fields
                                        ↓
                                   LLM Semantic → Enhanced Extraction
```

## Task Overview

| Task | Title | Priority | Status | Depends On | Duration |
|------|-------|----------|--------|------------|----------|
| [TASK-001](TASK-001-Multi-Format-Output-Support.md) | Multi-Format Output Support | High | ✅ **Complete** | - | 2 weeks |
| [TASK-002](TASK-002-Profile-Schema-Management-System.md) | Profile & Schema Management | High | 🟡 **Phase 7 Complete** | TASK-001 | 8 weeks |
| └─ [Phase 8](TASK-002-Profile-Schema-Management-System.md#phase-8) | Profile Statistics & Docs | High | ⏸️ Pending | Phase 1-7 | 1 week |
| └─ [Follow-up](TASK-002-PHASE-7-FOLLOWUP.md) | Critical Fixes (9 issues) | 🔴 **Critical** | ⏸️ Pending | Phase 7 | 2-3 weeks |
| [TASK-003](TASK-003-Structured-Field-Extraction.md) | Structured Field Extraction (Bedrock) | High | ⏸️ Not Started | TASK-001, TASK-002 | 4-6 weeks |
| [TASK-004](TASK-004-Batch-Processing-Support.md) | Batch Processing | Medium | ⏸️ Not Started | TASK-001, TASK-002 | 3-4 weeks |

**Progress**: 2/4 major tasks complete • **Next**: Fix critical issues before Phase 8

---

## Completed Work

### ✅ TASK-001: Multi-Format Output Support (COMPLETE)
**Completed**: 2026-01-29 • **Duration**: 2 weeks

Successfully implemented drop-in replacement for AWS Textract, Google Vision, and Azure OCR:

**Deliverables**:
- ✅ `formatters.py` - 4 output formatters (Textract, Google, Azure, DTAT)
- ✅ Normalized internal format with coordinate system
- ✅ API parameter: `GET /documents/{id}/content?format=textract`
- ✅ Backward compatible with existing integrations
- ✅ Unit tests for all formatters

**Business Impact**: DTAT can now output in any major OCR format, enabling seamless migration from cloud providers.

**Documentation**: [TASK-001-Multi-Format-Output-Support.md](TASK-001-Multi-Format-Output-Support.md)

---

### 🟡 TASK-002: Profile & Schema Management (Phase 1-7 COMPLETE)
**Completed Phases 1-7**: 2026-01-29 • **Duration**: 8 weeks

Built complete profile-based extraction system with 8 phases:

#### ✅ Phase 1: Database Schema & Models (Complete)
- PostgreSQL schema with profiles, fields, versions, usage tables
- Pydantic models with validation
- Base64JSON encoding for flexible storage
- Check constraints and indexes

#### ✅ Phase 2: Profile CRUD API (Complete)
- 10+ RESTful endpoints for profile management
- HTTP Basic Auth on all endpoints
- Profile versioning and rollback support
- OpenAPI/Swagger documentation

#### ✅ Phase 3: Coordinate & Keyword Extractors (Complete)
- CoordinateExtractor - exact position extraction
- KeywordProximityExtractor - "Invoice #:" followed by value
- Strategy pattern with pluggable extractors
- Confidence scoring for all extractions

#### ✅ Phase 4: Table, Regex & Transformers (Complete)
- TableColumnExtractor - extract from specific columns
- RegexPatternExtractor - pattern-based extraction
- Field transformers (currency, dates, emails, phones)
- Validators with min/max, allowed values, regex patterns

#### ✅ Phase 5: Profile Extraction Orchestrator (Complete)
- ProfileExtractor - coordinates all strategies
- Extraction statistics and reporting
- Validation status tracking
- Error handling and fallbacks

#### ✅ Phase 6: Built-in Profile Templates (Complete)
- 4 production-ready templates:
  - Generic Invoice (5 fields)
  - Retail Receipt (5 fields)
  - W-2 Tax Form (8 fields)
  - Driver's License (9 fields)
- Template instantiation and customization
- Database seeding with `python worker.py seed-templates`
- Template API endpoints

#### ✅ Phase 7: Document Processing Integration (Complete)
- Profile extraction integrated into main pipeline
- API: `POST /process-with-profile`
- API: `GET /documents/{id}/extracted-fields`
- CLI: `python worker.py process --profile invoice`
- Automatic extraction when profile assigned
- Usage tracking to profile_usage table
- 17 tests passing (3 simple, 10 template, 4 integration)

#### ⏸️ Phase 8: Profile Statistics & Documentation (Pending)
- Profile usage analytics dashboard
- Extraction success rate metrics
- Performance statistics per profile
- User guide and API examples

**Business Impact**: Users can now define custom extraction profiles and get structured data from documents automatically.

**Documentation**:
- [TASK-002-Profile-Schema-Management-System.md](TASK-002-Profile-Schema-Management-System.md) - Full specification
- [TASK-002-PHASE-6-SUMMARY.md](TASK-002-PHASE-6-SUMMARY.md) - Templates implementation
- [TASK-002-PHASE-7-SUMMARY.md](TASK-002-PHASE-7-SUMMARY.md) - Pipeline integration
- [docs/PROFILE-TEMPLATES.md](../PROFILE-TEMPLATES.md) - Template user guide

---

## 🔴 Critical Follow-ups (Before Production)

### TASK-002 Phase 7 Follow-up: Critical Fixes
**Priority**: 🔴 Critical • **Status**: Pending • **Effort**: 2-3 weeks

Code reviews identified **9 critical issues** that must be fixed before production deployment:

**Week 1 (Critical - 12-18 hours):**
- [x] Issue #1-3: Missing imports (Form, Body, Dict, Any) - **FIXED**
- [ ] Issue #4: Fix response model mismatch
- [ ] Issue #5: Add document validation after reload
- [ ] Issue #6: Fix circular imports
- [ ] Issue #7: Fix type mismatch (ocr_result)
- [ ] Issue #8: Fix tempfile leaks
- [ ] Issue #9: Fix bare except catching system exceptions
- [ ] Issue #10: ReDoS vulnerability (regex timeout)
- [ ] Issue #11: Database session leaks (missing rollback)

**Week 2-3 (High Priority - 25-33 hours):**
- [ ] Issue #12: Add API endpoint tests (45+ tests needed)
- [ ] Issue #13: Refactor profile resolution duplication
- [ ] Issue #14: Replace print() with proper logging
- [ ] Issue #15: Add transaction rollback in pipeline

**Documentation**: [TASK-002-PHASE-7-FOLLOWUP.md](TASK-002-PHASE-7-FOLLOWUP.md)

**Related Reviews**:
- [TASK-002-CODE-QUALITY-IMPROVEMENTS.md](TASK-002-CODE-QUALITY-IMPROVEMENTS.md)
- [TASK-002-DATABASE-IMPROVEMENTS.md](TASK-002-DATABASE-IMPROVEMENTS.md)
- [TASK-002-SECURITY-HARDENING.md](TASK-002-SECURITY-HARDENING.md)

---

## Detailed Task Breakdown

### TASK-001: Multi-Format Output Support
**Goal**: Enable DTAT to output in Textract, Google Vision, Azure OCR, and native formats

**Key Features**:
- Normalized internal format (coordinate system, block types)
- Format converters for each major OCR provider
- API parameter to select output format
- Backward compatibility with existing clients

**Business Value**:
- Drop-in replacement for AWS Textract (save $1.50/1000 pages)
- Easy migration from Google/Azure (no code changes)
- Future-proof architecture for new formats

**Technical Highlights**:
- Abstract `OutputFormatter` base class
- Coordinate normalization (0.0-1.0)
- Block type mapping (LINE → TEXT_LINE → line)
- Confidence score normalization

**Deliverables**:
- `TextractFormatter`, `GoogleVisionFormatter`, `AzureOCRFormatter`
- `/documents/{id}/content?format=textract` API endpoint
- Migration guide for existing integrations
- Unit tests for each formatter

---

### TASK-002: Profile & Schema Management System
**Goal**: Allow users to define reusable extraction profiles for specific document types

**Key Features**:
- Profile CRUD API (create, read, update, delete)
- Multiple extraction strategies:
  - Coordinate-based (fixed positions)
  - Keyword proximity ("Total:" followed by number)
  - Table column extraction
  - Regex pattern matching
  - LLM semantic extraction
- Field validation and transformation
- Profile versioning (audit trail)
- Built-in templates (invoice, receipt, W-2, etc.)

**Business Value**:
- Structured data extraction without custom code
- Reusable profiles across organizations
- Reduced time-to-value for new document types
- Self-service for business users

**Technical Highlights**:
- PostgreSQL JSONB for flexible schema storage
- Pydantic models for type safety
- Profile inheritance (clone and customize templates)
- Usage analytics per profile

**Deliverables**:
- Database schema with versioning
- Profile management API (10+ endpoints)
- 5+ built-in templates
- Field extractors for each strategy
- Visual profile editor (future phase)

---

### TASK-003: Structured Field Extraction (Bedrock Integration)
**Goal**: Use AWS Bedrock (Claude) for intelligent semantic field extraction

**Key Features**:
- Bedrock API integration (Converse API + Tool Use)
- LLM-based field extraction
- Cost optimization (Haiku vs Sonnet vs Opus)
- Fallback strategy (OCR → LLM only on low confidence)
- Cost tracking and budget enforcement

**Business Value**:
- Extract fields without rigid rules
- Handle layout variations automatically
- Multilingual support
- Competitive pricing vs Textract + post-processing

**Cost Analysis**:
```
1000 invoices/month:
- DTAT + Haiku:  $1.10/month (93% cheaper than Textract alone)
- DTAT + Sonnet: $13.50/month (comparable to Textract)
- Textract alone: $1.50/month (but no structured extraction)
- Textract + Bedrock (Lexitas approach): $15/month
```

**Technical Highlights**:
- Tool use for structured output (no JSON parsing)
- Token counting for cost estimation
- Model selection based on complexity
- Batch processing for efficiency

**Deliverables**:
- `BedrockExtractor` client wrapper
- `LLMFieldExtractor` strategy in profiles
- Cost tracking tables
- `/extract-fields` and `/extract-batch` endpoints
- Usage dashboards

---

### TASK-004: Batch Processing Support
**Goal**: Enable bulk document processing in single API request

**Key Features**:
- Multi-file upload (up to 1000 documents)
- ZIP file extraction
- Parallel processing (GPU utilization)
- Progress tracking (real-time status)
- Multiple export formats (JSON, CSV, Excel, ZIP)
- Auto-profile detection

**Business Value**:
- Enterprise scalability
- Efficient resource utilization
- Better user experience (upload once, get all results)
- Cost savings (batch Bedrock calls)

**Technical Highlights**:
- Async worker pool with semaphore
- FastAPI background tasks
- SQS integration (optional for scale)
- Result aggregation and export

**Deliverables**:
- Batch job management API
- Worker pool implementation
- Export functions (4 formats)
- Progress tracking UI
- Cleanup jobs for old batches

---

## Implementation Strategy

### ✅ Phase 1: Foundation (COMPLETE)
**Focus**: TASK-001 + Core infrastructure
**Duration**: Weeks 1-8 (2 months)
**Status**: ✅ Complete

```
Week 1-2:  ✅ Design normalized format, coordinate mapping
Week 3-4:  ✅ Implement TextractFormatter
Week 5-6:  ✅ Implement GoogleVisionFormatter, AzureOCRFormatter
Week 7-8:  ✅ Testing, documentation, migration guide
```

**Milestone**: ✅ DTAT can output in any major OCR format

### ✅ Phase 2: Profiles (COMPLETE)
**Focus**: TASK-002 Phases 1-7
**Duration**: Weeks 9-16 (8 weeks)
**Status**: ✅ Complete

```
Week 9-10:   ✅ Database schema, models, API (Phases 1-2)
Week 11-12:  ✅ Extraction strategies (coordinate, keyword, table, regex) (Phases 3-4)
Week 13-14:  ✅ Built-in templates, validation (Phases 5-6)
Week 15-16:  ✅ Pipeline integration, testing (Phase 7)
```

**Milestone**: ✅ Users can create custom extraction profiles

### Phase 3: Intelligence (Months 4-5)
**Focus**: TASK-003 + Bedrock integration

```
Week 17-18:  Bedrock client, tool use implementation
Week 19-20:  LLM extraction strategy, cost tracking
Week 21-22:  Optimization (model selection, token limits)
Week 23-24:  Testing, cost analysis, documentation
```

**Milestone**: Intelligent semantic extraction available

### Phase 4: Scale (Month 5-6)
**Focus**: TASK-004 + Batch processing

```
Week 25-26:  Batch API, worker pool
Week 27-28:  Export formats, progress tracking
Week 29-30:  Testing, optimization
Week 31-32:  Polish, documentation, launch
```

**Milestone**: Production-ready batch processing

---

## Success Metrics

### Performance
- **Throughput**: 1000+ pages/hour (with GPU)
- **Latency**: < 2s per page (OCR) + < 3s (profile extraction)
- **Reliability**: 99.5% success rate
- **GPU Utilization**: 70%+ during batch processing

### Cost
- **OCR Cost**: $0 (local GPU) vs $1.50/1000 pages (Textract)
- **LLM Cost**: $0.001-$0.02 per document (Haiku-Sonnet)
- **Total Cost**: 85-95% cheaper than Textract + commercial OCR

### Adoption
- **Profiles Created**: 100+ custom profiles
- **Monthly Documents**: 10,000+ processed
- **Format Mix**: 40% Textract, 30% Google, 20% Azure, 10% native
- **User Satisfaction**: 4.5+ stars

---

## Dependencies & Prerequisites

### Infrastructure
- [ ] AWS EC2 g4dn.xlarge instance (Tesla T4 GPU)
- [ ] PostgreSQL database (for profiles)
- [ ] AWS Bedrock access (for LLM extraction)
- [ ] S3 bucket (optional for large batches)

### Technical
- [ ] Python 3.12+
- [ ] FastAPI
- [ ] SQLAlchemy + Alembic (migrations)
- [ ] boto3 (Bedrock client)
- [ ] pandas, openpyxl (export formats)

### Development
- [ ] Git workflow (feature branches)
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Testing framework (pytest)
- [ ] Documentation (Sphinx or MkDocs)

---

## Risk Management

### Technical Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| LightOnOCR quality issues | High | Medium | Fallback to Textract, model fine-tuning |
| Bedrock API rate limits | Medium | Low | Request increase, implement caching |
| GPU memory constraints | High | Medium | Batch size optimization, model quantization |
| Profile complexity explosion | Medium | Medium | Template library, validation rules |

### Business Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Cost overruns (Bedrock) | High | Medium | Budget alerts, Haiku model default |
| User adoption low | High | Low | Templates, documentation, demos |
| Competition (new OCR services) | Medium | Medium | Focus on flexibility, profiles |

---

## Future Enhancements (Post-MVP)

### Visual Profile Editor
- Drag-and-drop field positioning on document preview
- Real-time extraction preview
- Auto-suggest extraction strategies

### Machine Learning
- Learn extraction patterns from corrections
- Auto-generate profiles from examples
- Anomaly detection

### Advanced Features
- Cross-field validation (line items sum to total)
- Multi-page correlation
- Hierarchical data (nested objects)
- Conditional extraction rules

### Integrations
- Webhook notifications
- Zapier/Make.com connectors
- Export to popular formats (QuickBooks, Xero)
- Slack/Teams notifications

---

## Reference Documents

### Internal
- [OCR API Formats](../OCR-API-FORMATS.md) - Detailed comparison of Textract/Google/Azure
- [DEPLOYMENT-LOG.md](../../DEPLOYMENT-LOG.md) - AWS deployment history
- [README.md](../../README.md) - Project overview
- [CLAUDE.md](../../CLAUDE.md) - Project instructions

### External Reference
- [Lexitas-OCR](../../../../Client%20POCs/Lexitas-OCR/) - Reference architecture for Textract + Bedrock pipeline

### API Documentation
- [AWS Textract API](https://docs.aws.amazon.com/textract/latest/dg/API_Reference.html)
- [Google Cloud Vision API](https://cloud.google.com/vision/docs/reference/rest)
- [Azure Computer Vision API](https://learn.microsoft.com/en-us/azure/ai-services/computer-vision/overview-ocr)
- [AWS Bedrock API](https://docs.aws.amazon.com/bedrock/latest/APIReference/)

---

## Getting Started

To begin implementation:

1. **Review all task documents** to understand full scope
2. **Set up development environment** (GPU instance, PostgreSQL)
3. **Create feature branch** for TASK-001
4. **Implement normalized format** as foundation
5. **Build incrementally** with tests at each step

For questions or clarifications, refer to:
- Task-specific documents in `docs/tasks/`
- API format research in `docs/OCR-API-FORMATS.md`
- Deployment logs in `DEPLOYMENT-LOG.md`

---

## Current Status Summary

**Completed**: 2/4 major tasks (TASK-001, TASK-002 Phases 1-7)
**In Progress**: Critical follow-up fixes (9 issues)
**Pending**: TASK-002 Phase 8, TASK-003, TASK-004

**Overall Progress**: ~60% complete (10/16 weeks)

---

**Last Updated**: 2026-01-29 17:00
**Status**: TASK-002 Phase 7 Complete • Critical Fixes in Progress
**Next Step**: Fix 9 critical issues in TASK-002-PHASE-7-FOLLOWUP.md before Phase 8

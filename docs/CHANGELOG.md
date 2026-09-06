# Changelog

This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and uses semantic versioning for tagged releases.

## Unreleased

### Added

- Azure AI Document Intelligence extraction and Azure-compatible analyze endpoints.
- Responsive web navigation and settings controls.
- Isolated test configuration and development dependencies.

### Changed

- Cloud OCR providers are opt-in by default.
- Docker Compose uses its PostgreSQL service without publishing the database port.
- API documentation and built-in template routes now require authentication.
- Container images run as an unprivileged user and copy all required application modules.

### Security

- Removed known default passwords and made startup fail closed when authentication is not configured.
- Bounded request-body reads before buffering uploads in memory.
- Made Azure-compatible endpoints fail closed and compare keys in constant time.
- Redacted database passwords from startup logs.
- Removed reconstructed worker temporary files after processing.

## 2.1.0

### Added

- Multi-format OCR output compatible with AWS Textract, Google Cloud Vision, and Azure OCR shapes.
- Reusable extraction profiles, built-in templates, field validation, and transformation.
- Synchronous and queued processing APIs backed by SQLite or PostgreSQL.
- Browser UI for uploads, document history, settings, and API documentation.

### Changed

- Replaced PyMuPDF with pdfplumber to keep the dependency set compatible with permissive redistribution.

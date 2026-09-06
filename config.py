"""
Configuration for Document Processing Pipeline
"""

from dataclasses import dataclass, field
from typing import Optional
import os


def _env_bool(name: str, default: bool) -> bool:
    """Read a boolean environment variable with a predictable fallback."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class ProcessingConfig:
    """Pipeline configuration - easily toggle features."""

    # Extraction levels (enable/disable)
    enable_native_extraction: bool = True    # Level 1: Free parsing
    enable_local_ocr: bool = field(default_factory=lambda: _env_bool("ENABLE_LOCAL_OCR", False))
    enable_textract: bool = field(default_factory=lambda: _env_bool("ENABLE_TEXTRACT", False))

    # Retry settings
    max_retries_per_level: int = 2
    retry_delay_seconds: int = 5

    # Quality thresholds (0-100)
    min_confidence_score: int = 60           # Below this, escalate to next level
    min_chars_per_page: int = 100            # Below this, likely failed extraction
    max_gibberish_ratio: float = 0.15        # Above this, likely garbage output

    # OCR Model settings
    ocr_model_name: str = "lightonai/LightOnOCR-1B-1025"
    ocr_max_new_tokens: int = 2048
    ocr_image_max_dim: int = 1540
    ocr_offline_mode: bool = field(default_factory=lambda: _env_bool("OCR_OFFLINE_MODE", True))

    # AWS settings (for Textract)
    aws_region: str = field(default_factory=lambda: os.getenv("AWS_REGION", "us-east-1"))
    textract_features: list = field(default_factory=lambda: ["TABLES", "FORMS"])
    s3_bucket: str = field(default_factory=lambda: os.getenv("S3_BUCKET", ""))
    s3_prefix: str = field(default_factory=lambda: os.getenv("S3_PREFIX", "dtat-ocr/temp/"))

    # Azure Document Intelligence settings
    enable_azure_di: bool = field(default_factory=lambda: os.getenv("AZURE_DI_ENABLED", "false").lower() == "true")
    azure_di_endpoint: str = field(default_factory=lambda: os.getenv("AZURE_DI_ENDPOINT", ""))
    azure_di_key: str = field(default_factory=lambda: os.getenv("AZURE_DI_KEY", ""))
    azure_di_api_version: str = field(default_factory=lambda: os.getenv("AZURE_DI_API_VERSION", "2024-11-30"))
    azure_di_default_model: str = field(default_factory=lambda: os.getenv("AZURE_DI_DEFAULT_MODEL", "prebuilt-layout"))
    azure_di_poll_interval_s: float = 1.0
    azure_di_poll_timeout_s: int = 120

    # Database settings
    database_url: str = field(default_factory=lambda: os.getenv(
        "DATABASE_URL",
        "sqlite:///documents.db"
    ))

    # Storage settings
    store_original_file: bool = field(default_factory=lambda: _env_bool("STORE_ORIGINAL_FILE", True))
    max_file_size_mb: int = field(default_factory=lambda: int(os.getenv("MAX_FILE_SIZE_MB", "50")))
    max_pdf_pages: int = field(default_factory=lambda: int(os.getenv("MAX_PDF_PAGES", "200")))
    max_image_pixels: int = field(default_factory=lambda: int(os.getenv("MAX_IMAGE_PIXELS", "50000000")))
    max_image_frames: int = field(default_factory=lambda: int(os.getenv("MAX_IMAGE_FRAMES", "50")))
    max_archive_uncompressed_mb: int = field(default_factory=lambda: int(os.getenv("MAX_ARCHIVE_UNCOMPRESSED_MB", "250")))
    max_csv_rows: int = field(default_factory=lambda: int(os.getenv("MAX_CSV_ROWS", "100000")))

    # Edge case handling
    enable_dedup: bool = True                # Skip re-processing identical documents
    enable_handwriting: bool = True          # Add HANDWRITING to Textract FeatureTypes for images
    blank_page_threshold: int = 10           # Pages with fewer chars flagged as blank
    default_language: str = field(default_factory=lambda: os.getenv("OCR_LANGUAGE", "en"))  # Language hint
    force_cpu: bool = field(default_factory=lambda: os.getenv("FORCE_CPU", "false").lower() == "true")  # Override GPU auto-detect

    # Processing settings
    batch_size: int = 10                     # Process N docs before committing
    worker_timeout_seconds: int = 300        # 5 min max per document


# Default config - can be overridden
config = ProcessingConfig()


def enable_textract():
    """Enable Textract fallback (for production use)."""
    config.enable_textract = True
    print("Textract fallback ENABLED")


def disable_textract():
    """Disable Textract fallback (for cost savings)."""
    config.enable_textract = False
    print("Textract fallback DISABLED")

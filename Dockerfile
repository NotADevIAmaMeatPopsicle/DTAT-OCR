# =============================================================================
# DTAT OCR (Ducktape and Twine OCR) - Docker Image
# =============================================================================
# Multi-stage build:
# 1. Download model weights (cached layer)
# 2. Build final image with code + model + Web UI
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Download model weights
# -----------------------------------------------------------------------------
FROM python:3.14-slim AS model-downloader

# Install minimal dependencies for downloading
RUN pip install --no-cache-dir huggingface_hub transformers && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Download model weights to cache directory
ENV HF_HOME=/model-cache
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('lightonai/LightOnOCR-1B-1025', local_dir='/model-cache/lightonai/LightOnOCR-1B-1025'); print('Model downloaded successfully')"

# -----------------------------------------------------------------------------
# Stage 2: Final image
# -----------------------------------------------------------------------------
FROM python:3.14-slim

# OCI image metadata
LABEL org.opencontainers.image.title="DTAT OCR"
LABEL org.opencontainers.image.description="Self-hosted document processing with native and optional OCR engines"
LABEL org.opencontainers.image.source="https://github.com/NotADevIAmaMeatPopsicle/DTAT-OCR"
LABEL org.opencontainers.image.licenses="MIT"

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV HF_HOME=/app/model-cache
ENV HF_HUB_OFFLINE=1

# Working directory
WORKDIR /app

# Run the service as an unprivileged user.
RUN groupadd --system dtat && useradd --system --gid dtat --home-dir /app --shell /usr/sbin/nologin dtat

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # For image processing
    libjpeg-dev \
    libpng-dev \
    # General
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy model weights from downloader stage
COPY --from=model-downloader --chown=dtat:dtat /model-cache /app/model-cache

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=dtat:dtat *.py ./

# Copy Web UI templates
COPY --chown=dtat:dtat templates/ ./templates/

# Create directories
RUN mkdir -p /app/data /app/temp && chown -R dtat:dtat /app/data /app/temp

# Volume for persistent data (SQLite DB)
VOLUME /app/data

# Environment variables (can be overridden)
ENV DATABASE_URL=sqlite:////app/data/documents.db
ENV OCR_OFFLINE_MODE=true
ENV ENABLE_TEXTRACT=false

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose API port
EXPOSE 8000

USER dtat

# Default command - run API server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

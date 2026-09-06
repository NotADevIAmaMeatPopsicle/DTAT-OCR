"""Regression tests for security-sensitive defaults and request handling."""

import uuid

import pytest
from fastapi.testclient import TestClient

import api
from config import config
from database import init_database


client = TestClient(api.app)
AUTH = (api.API_USERNAME, api.API_PASSWORD)


@pytest.mark.parametrize("path", ["/", "/docs", "/openapi.json", "/templates"])
def test_sensitive_routes_require_authentication(path):
    response = client.get(path)
    assert response.status_code == 401


def test_health_is_intentionally_public():
    init_database()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["database"] in {"connected", "unavailable"}


def test_known_password_is_rejected_at_startup(monkeypatch):
    monkeypatch.setattr(api, "API_PASSWORD", "changeme123")
    with pytest.raises(RuntimeError, match="known default"):
        api._validate_auth_configuration()


def test_raw_upload_limit_is_checked_while_streaming(monkeypatch):
    monkeypatch.setattr(config, "max_file_size_mb", 0)
    response = client.post(
        "/ocr",
        content=b"not-buffered-past-the-limit",
        headers={"content-type": "image/png"},
        auth=AUTH,
    )
    assert response.status_code == 413


def test_azure_compatibility_endpoint_fails_closed_without_key(monkeypatch):
    monkeypatch.delenv("DTAT_AZURE_COMPAT_KEY", raising=False)
    response = client.post(
        "/documentintelligence/documentModels/prebuilt-read:analyze",
        content=b"payload",
        headers={"content-type": "image/png"},
    )
    assert response.status_code == 401


def test_async_job_schema_is_created_and_portable():
    init_database()
    job_id = str(uuid.uuid4())
    api._create_job(job_id)
    created = api._get_job(job_id)
    assert created["status"] == "processing"

    api._complete_job(job_id, document_id=None, text="done", confidence=99, processing_time_ms=12)
    completed = api._get_job(job_id)
    assert completed["status"] == "completed"
    assert completed["extracted_text"] == "done"

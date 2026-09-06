"""Safe, isolated defaults for the test suite."""

import os
import shutil
import tempfile
from pathlib import Path


_test_data_dir = tempfile.TemporaryDirectory(prefix="dtat-ocr-tests-")
_database_path = Path(_test_data_dir.name, "tests.db").as_posix()

os.environ.setdefault("DATABASE_URL", f"sqlite:///{_database_path}")
os.environ.setdefault("DTAT_USERNAME", "test-user")
os.environ.setdefault("DTAT_PASSWORD", "test-password-only-123")
os.environ.setdefault("ENABLE_TEXTRACT", "false")
os.environ.setdefault("ENABLE_LOCAL_OCR", "false")


def pytest_sessionfinish(session, exitstatus):
    """Release SQLite handles before removing the temporary test database."""
    import database

    if database._engine is not None:
        database._engine.dispose()
    shutil.rmtree(_test_data_dir.name, ignore_errors=True)

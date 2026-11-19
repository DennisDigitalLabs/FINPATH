import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest


ROOT = Path(__file__).resolve().parents[1]
os.environ.update({
    "ENVIRONMENT": "testing",
    "DEBUG": "false",
    "DATABASE_URL": "sqlite://",
    "SECRET_KEY": "test-secret-key-for-isolated-tests-only-123456",
    "ADMIN_OWNER_EMAIL": "test-owner@example.test",
    "ADMIN_BOOTSTRAP_TOKEN": "test-only-bootstrap-token-with-32-chars",
    "FRONTEND_URL": "http://localhost:3000",
    "CORS_ORIGINS": json.dumps(["http://localhost:3000"]),
    "SQLALCHEMY_ECHO": "false",
    "MODEL_PATH": str(ROOT / "models" / "v1"),
    "SMTP_HOST": "",
    "SMTP_USERNAME": "",
    "SMTP_PASSWORD": "",
    "SMTP_FROM_EMAIL": "",
})
for _component in ("DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME"):
    os.environ.pop(_component, None)


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    database_url = os.environ.get("DATABASE_URL", "")
    parsed = urlsplit(database_url)
    if not database_url or not (
        database_url.startswith("sqlite://")
        or database_url == ":memory:"
    ):
        pytest.exit(
            "Refusing test run: FINPATH tests require an SQLite URL.",
            returncode=2,
        )
    if parsed.hostname:
        pytest.exit(
            "Refusing test run: test database hosts are prohibited.",
            returncode=2,
        )

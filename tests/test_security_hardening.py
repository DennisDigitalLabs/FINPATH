from datetime import datetime, timedelta, timezone
import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from jose import jwt
from pydantic import ValidationError

from backend.config import Settings, get_settings
from backend import database
from backend.dependencies import get_current_user
from backend.main import app
from backend.security import verify_password


client = TestClient(app)


def test_security_headers_are_present_on_api_responses():
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"


def test_cors_allows_configured_origin_and_admin_status_updates():
    response = client.options(
        "/api/v1/admin/users/1/status",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "Authorization" in response.headers["access-control-allow-headers"]
    assert "PATCH" in response.headers["access-control-allow-methods"]


def test_production_rejects_debug_and_wildcard_cors():
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            DEBUG=True,
            SECRET_KEY="x" * 40,
            CORS_ORIGINS=["https://app.example"],
        )

    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="x" * 40,
            CORS_ORIGINS=["*"],
        )


def test_production_requires_postgresql_and_enforces_database_tls(monkeypatch):
    for name in ("DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME"):
        monkeypatch.delenv(name, raising=False)
    common = {
        "ENVIRONMENT": "production",
        "DEBUG": False,
        "SECRET_KEY": "x" * 40,
        "CORS_ORIGINS": ["https://app.example"],
        "FRONTEND_URL": "https://app.example",
    }

    with pytest.raises(ValidationError, match="PostgreSQL"):
        Settings(**common, DATABASE_URL="sqlite://")

    settings = Settings(
        **common,
        DATABASE_URL="postgresql://test-user:test-password@db.example/finpath",
    )
    assert settings.get_database_url().endswith("?sslmode=require")

    with pytest.raises(ValidationError, match="SSL"):
        Settings(
            **common,
            DATABASE_URL=(
                "postgresql://test-user:test-password@db.example/finpath"
                "?sslmode=disable"
            ),
        )


def test_production_rejects_non_https_origins_and_sql_echo():
    with pytest.raises(ValidationError, match="HTTPS"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="x" * 40,
            DATABASE_URL="postgresql://test-user:test-password@db.example/finpath",
            CORS_ORIGINS=["http://app.example"],
            FRONTEND_URL="https://app.example",
        )

    with pytest.raises(ValidationError, match="SQLALCHEMY_ECHO"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="x" * 40,
            DATABASE_URL="postgresql://test-user:test-password@db.example/finpath",
            CORS_ORIGINS=["https://app.example"],
            SQLALCHEMY_ECHO=True,
            FRONTEND_URL="https://app.example",
        )


def test_production_startup_does_not_create_schema(monkeypatch):
    called = False

    def fail_create_all(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("Production startup must use Alembic migrations")

    monkeypatch.setattr(database, "settings", SimpleNamespace(is_production=True))
    monkeypatch.setattr(database.Base.metadata, "create_all", fail_create_all)
    asyncio.run(database.init_db())
    assert called is False


def test_example_secret_key_placeholder_is_rejected():
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="testing",
            DEBUG=False,
            SECRET_KEY="replace-with-a-random-secret-at-least-32-characters",
        )


def test_short_admin_bootstrap_token_is_rejected():
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="testing",
            DEBUG=False,
            SECRET_KEY="x" * 40,
            ADMIN_BOOTSTRAP_TOKEN="too-short",
        )


def test_malformed_stored_password_hash_fails_closed():
    assert verify_password("password", "not-a-valid-password-hash") is False


def test_invalid_jwt_signature_is_rejected():
    invalid_token = jwt.encode(
        {
            "sub": "1",
            "role": "user",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        "wrong-signing-key" * 4,
        algorithm=get_settings().ALGORITHM,
    )
    with pytest.raises(HTTPException) as error:
        get_current_user(token=invalid_token, db=None)
    assert error.value.status_code == 401


def test_error_response_does_not_include_internal_details():
    response = client.get("/health")
    assert "Traceback" not in response.text
    assert "SECRET_KEY" not in response.text
    assert "password" not in response.text.lower()

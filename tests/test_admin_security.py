import os
import runpy
from pathlib import Path

os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("SECRET_KEY", "abcdefghijklmnopqrstuvwxyz123456")
os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import create_admin as admin_cli
from backend.database import Base, SessionLocal, engine
from backend.dependencies import get_db
from backend.main import app
from backend.models import User
from backend.services import auth_service
from backend.schemas.user import AdminCreate, UserCreate
from backend.security import decode_access_token, verify_password
from backend.services.auth_service import count_admin_users, create_admin_user, register_user


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
        session.rollback()
        session.query(User).delete()
        session.commit()
    finally:
        session.close()


@pytest.fixture()
def client(db):
    previous_override = app.dependency_overrides.get(get_db)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override


def _create_admin(db, email, password):
    return create_admin_user(
        db,
        AdminCreate(full_name="Test Admin", email=email, password=password),
    )


def _login(client, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_public_registration_creates_normal_user(db):
    user = register_user(
        db,
        UserCreate(
            full_name="Public User",
            email="public@example.com",
            password="StrongPass123",
        ),
    )

    assert user.role == "user"

def test_count_admin_users_counts_only_active_admins(db):
    db.add_all([
        User(
            full_name="Inactive Admin One",
            email="inactive-admin1@example.com",
            hashed_password="hash",
            role="admin",
            is_active=False,
        ),
        User(
            full_name="Inactive Admin Two",
            email="inactive-admin2@example.com",
            hashed_password="hash",
            role="admin",
            is_active=False,
        ),
        User(
            full_name="Active Admin One",
            email="active-admin1@example.com",
            hashed_password="hash",
            role="admin",
            is_active=True,
        ),
        User(
            full_name="Active Admin Two",
            email="active-admin2@example.com",
            hashed_password="hash",
            role="admin",
            is_active=True,
        ),
    ])
    db.commit()
    assert count_admin_users(db) == 2


def test_first_admin_cli_creates_hashed_admin_that_can_login_and_access_admin_endpoint(
    client, db, monkeypatch
):
    inputs = iter(["first-admin@example.com", "First Admin"])
    passwords = iter(["FirstAdmin123", "FirstAdmin123"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))
    monkeypatch.setattr(admin_cli, "getpass", lambda _prompt: next(passwords))

    assert admin_cli.main() == 0

    admin = db.query(User).filter(User.email == "first-admin@example.com").one()
    assert admin.role == "admin"
    assert admin.is_active is True
    assert admin.hashed_password != "FirstAdmin123"
    assert verify_password("FirstAdmin123", admin.hashed_password)

    token = _login(client, "first-admin@example.com", "FirstAdmin123")
    claims = decode_access_token(token)
    assert claims["sub"] == str(admin.id)
    assert claims["role"] == "admin"
    response = client.get("/api/v1/analytics/system", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

    repeat_inputs = iter(["second-admin@example.com", "Second Admin"])
    repeat_passwords = iter(["SecondAdmin123", "SecondAdmin123"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(repeat_inputs))
    monkeypatch.setattr(admin_cli, "getpass", lambda _prompt: next(repeat_passwords))
    assert admin_cli.main() == 1
    assert count_admin_users(db) == 1


def test_admin_endpoint_requires_admin_and_enforces_two_active_limit(client, db):
    first_admin = _create_admin(db, "first@example.com", "FirstAdmin123")
    admin_token = _login(client, first_admin.email, "FirstAdmin123")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    second_data = {
        "full_name": "Second Admin",
        "email": "second@example.com",
        "password": "SecondAdmin123",
    }

    assert client.post("/api/v1/auth/admins", json=second_data).status_code == 401

    user_response = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Normal User", "email": "user@example.com", "password": "NormalUser123"},
    )
    assert user_response.status_code == 201
    user_token = _login(client, "user@example.com", "NormalUser123")
    assert client.post(
        "/api/v1/auth/admins",
        json=second_data,
        headers={"Authorization": f"Bearer {user_token}"},
    ).status_code == 403

    assert client.post(
        "/api/v1/auth/admins",
        json={**second_data, "role": "admin"},
        headers=admin_headers,
    ).status_code == 422

    second_response = client.post("/api/v1/auth/admins", json=second_data, headers=admin_headers)
    assert second_response.status_code == 201
    second_admin = second_response.json()
    assert second_admin["role"] == "admin"
    assert second_admin["is_active"] is True
    assert "hashed_password" not in second_admin
    stored_second = db.query(User).filter(User.email == "second@example.com").one()
    assert stored_second.hashed_password != second_data["password"]
    assert verify_password(second_data["password"], stored_second.hashed_password)
    second_token = _login(client, "second@example.com", second_data["password"])
    assert decode_access_token(second_token)["role"] == "admin"
    assert client.get(
        "/api/v1/analytics/system",
        headers={"Authorization": f"Bearer {second_token}"},
    ).status_code == 200

    assert client.post("/api/v1/auth/admins", json=second_data, headers=admin_headers).status_code == 409
    third_data = {**second_data, "email": "third@example.com"}
    assert client.post("/api/v1/auth/admins", json=third_data, headers=admin_headers).status_code == 409
    assert count_admin_users(db) == 2


def test_inactive_admin_cannot_login_or_use_admin_endpoint(client, db):
    admin = _create_admin(db, "inactive-admin@example.com", "InactiveAdmin123")
    token = _login(client, admin.email, "InactiveAdmin123")
    db.query(User).filter(User.id == admin.id).update({"is_active": False})
    db.commit()

    assert client.post(
        "/api/v1/auth/login",
        json={"email": admin.email, "password": "InactiveAdmin123"},
    ).status_code == 401
    assert client.get(
        "/api/v1/analytics/system",
        headers={"Authorization": f"Bearer {token}"},
    ).status_code == 401


def test_admin_limit_migration_blocks_third_and_reactivation(monkeypatch):
    migration_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=migration_engine)
    session_factory = sessionmaker(bind=migration_engine, autoflush=False, autocommit=False)
    db = session_factory()
    migration_path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "7f2c1d9a6b4e_limit_active_admins.py"

    try:
        with migration_engine.begin() as connection:
            migration_context = MigrationContext.configure(connection)
            with Operations.context(migration_context):
                runpy.run_path(str(migration_path))["upgrade"]()

        first = User(
            full_name="First Admin",
            email="migration-admin1@example.com",
            hashed_password="hash",
            role="admin",
            is_active=True,
        )
        db.add_all([
            first,
            User(
                full_name="Second Admin",
                email="migration-admin2@example.com",
                hashed_password="hash",
                role="admin",
                is_active=True,
            ),
        ])
        db.commit()

        db.add(User(
            full_name="Third Admin",
            email="migration-admin3@example.com",
            hashed_password="hash",
            role="admin",
            is_active=True,
        ))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        with monkeypatch.context() as scoped_patch:
            scoped_patch.setattr(auth_service, "count_admin_users", lambda _session: 1)
            with pytest.raises(ValueError, match="Maximum of 2 active admin accounts"):
                auth_service.create_admin_user(
                    db,
                    AdminCreate(
                        full_name="Concurrent Third Admin",
                        email="concurrent-admin3@example.com",
                        password="ConcurrentAdmin123",
                    ),
                )

        db.query(User).filter(User.id == first.id).update({"is_active": False})
        db.commit()
        auth_service.create_admin_user(
            db,
            AdminCreate(
                full_name="Replacement Admin",
                email="replacement-admin@example.com",
                password="ReplacementAdmin123",
            ),
        )
        assert auth_service.count_admin_users(db) == 2

        with pytest.raises(IntegrityError):
            db.query(User).filter(User.id == first.id).update({"is_active": True})
            db.commit()
        db.rollback()
        assert auth_service.count_admin_users(db) == 2
    finally:
        db.close()
        Base.metadata.drop_all(bind=migration_engine)
        migration_engine.dispose()

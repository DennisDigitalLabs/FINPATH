import os
import runpy
from pathlib import Path
from types import SimpleNamespace

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
from backend import dependencies as auth_dependencies
from backend.database import Base, SessionLocal, engine
from backend.dependencies import get_db
from backend.main import app
from backend.models import User
from backend.services import auth_service
from backend.schemas.user import AdminCreate, UserCreate
from backend.security import decode_access_token, hash_password, verify_password
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


def _configure_admin_owner(monkeypatch, email):
    settings = SimpleNamespace(ADMIN_OWNER_EMAIL=email.strip().lower())
    monkeypatch.setattr(auth_dependencies, "get_settings", lambda: settings)
    monkeypatch.setattr(auth_service, "get_settings", lambda: settings)
    monkeypatch.setattr(admin_cli, "get_settings", lambda: settings)


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
    _configure_admin_owner(monkeypatch, "first-admin@example.com")
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


def test_admin_cli_promotes_only_the_confirmed_configured_owner(client, db, monkeypatch):
    _configure_admin_owner(monkeypatch, "owner@example.com")
    register_user(
        db,
        UserCreate(full_name="Owner", email="owner@example.com", password="OwnerPassword123"),
    )
    inputs = iter(["owner@example.com", "yes"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))

    assert admin_cli.main() == 0
    db.expire_all()
    owner = db.query(User).filter(User.email == "owner@example.com").one()
    assert owner.role == "admin"

    token = _login(client, owner.email, "OwnerPassword123")
    response = client.get("/api/v1/analytics/system", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_admin_cli_requires_explicit_confirmation_to_revoke_other_admins(db, monkeypatch):
    _configure_admin_owner(monkeypatch, "owner@example.com")
    owner = register_user(
        db,
        UserCreate(full_name="Owner", email="owner@example.com", password="OwnerPassword123"),
    )
    other_admin = User(
        full_name="Other Admin",
        email="other-admin@example.com",
        hashed_password=hash_password("OtherAdmin123"),
        role="admin",
        is_active=True,
    )
    db.add(other_admin)
    db.commit()
    inputs = iter(["owner@example.com", "REVOKE", "yes"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))

    assert admin_cli.main() == 0
    db.expire_all()
    assert db.get(User, owner.id).role == "admin"
    assert db.get(User, other_admin.id).role == "user"


def test_only_configured_admin_owner_can_access_admin_api_and_admin_creation_is_disabled(
    client, db, monkeypatch
):
    _configure_admin_owner(monkeypatch, "first@example.com")
    first_admin = _create_admin(db, "first@example.com", "FirstAdmin123")
    owner_token = _login(client, first_admin.email, "FirstAdmin123")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    user_response = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Normal User", "email": "user@example.com", "password": "NormalUser123"},
    )
    assert user_response.status_code == 201
    user_token = _login(client, "user@example.com", "NormalUser123")
    assert client.get(
        "/api/v1/analytics/system",
        headers={"Authorization": f"Bearer {user_token}"},
    ).status_code == 403

    other_admin = User(
        full_name="Other Admin",
        email="other-admin@example.com",
        hashed_password=hash_password("OtherAdmin123"),
        role="admin",
        is_active=True,
    )
    db.add(other_admin)
    db.commit()
    other_token = _login(client, other_admin.email, "OtherAdmin123")

    assert client.get(
        "/api/v1/analytics/system",
        headers={"Authorization": f"Bearer {other_token}"},
    ).status_code == 403
    assert client.get("/api/v1/analytics/system", headers=owner_headers).status_code == 200
    assert client.post("/api/v1/auth/admins", json={}).status_code == 404
    assert count_admin_users(db) == 2


def test_admin_access_fails_closed_when_owner_is_not_configured(client, db, monkeypatch):
    _configure_admin_owner(monkeypatch, "admin@example.com")
    admin = _create_admin(db, "admin@example.com", "AdminPassword123")
    token = _login(client, admin.email, "AdminPassword123")
    monkeypatch.setattr(
        auth_dependencies,
        "get_settings",
        lambda: SimpleNamespace(ADMIN_OWNER_EMAIL=""),
    )

    response = client.get(
        "/api/v1/analytics/system",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 503
    assert client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    ).status_code == 503
    assert client.get(
        "/api/v1/admin/health",
        headers={"Authorization": f"Bearer {token}"},
    ).status_code == 503


def test_inactive_admin_cannot_login_or_use_admin_endpoint(client, db, monkeypatch):
    _configure_admin_owner(monkeypatch, "inactive-admin@example.com")
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
            settings = SimpleNamespace(ADMIN_OWNER_EMAIL="concurrent-admin3@example.com")
            scoped_patch.setattr(auth_service, "get_settings", lambda: settings)
            scoped_patch.setattr(auth_service, "count_admin_users", lambda _session: 1)
            with pytest.raises(ValueError, match="active admin account already exists"):
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
        with monkeypatch.context() as scoped_patch:
            scoped_patch.setattr(
                auth_service,
                "get_settings",
                lambda: SimpleNamespace(ADMIN_OWNER_EMAIL="replacement-admin@example.com"),
            )
            with pytest.raises(ValueError, match="active admin account already exists"):
                auth_service.create_admin_user(
                    db,
                    AdminCreate(
                        full_name="Replacement Admin",
                        email="replacement-admin@example.com",
                        password="ReplacementAdmin123",
                    ),
                )
        db.add(
            User(
                full_name="Replacement Admin",
                email="replacement-admin@example.com",
                hashed_password="hash",
                role="admin",
                is_active=True,
            )
        )
        db.commit()
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


def test_admin_user_search_is_paginated_and_never_returns_credentials(client, db, monkeypatch):
    _configure_admin_owner(monkeypatch, "owner@example.com")
    admin = _create_admin(db, "owner@example.com", "OwnerPassword123")
    token = _login(client, admin.email, "OwnerPassword123")
    db.add_all([
        User(
            full_name="Search Match One",
            email="match-one@example.com",
            hashed_password=hash_password("MatchPassword123"),
            role="user",
            is_active=True,
        ),
        User(
            full_name="Search Match Two",
            email="match-two@example.com",
            hashed_password=hash_password("MatchPassword123"),
            role="user",
            is_active=False,
        ),
        User(
            full_name="Other Person",
            email="other@example.com",
            hashed_password=hash_password("OtherPassword123"),
            role="user",
            is_active=True,
        ),
    ])
    db.commit()
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        "/api/v1/admin/users",
        params={"search": "match", "page": 1, "page_size": 1},
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["page"] == 1
    assert payload["page_size"] == 1
    assert len(payload["items"]) == 1
    assert "hashed_password" not in payload["items"][0]
    assert "password" not in payload["items"][0]

    second_page = client.get(
        "/api/v1/admin/users",
        params={"search": "match", "page": 2, "page_size": 1},
        headers=headers,
    )
    assert second_page.status_code == 200
    assert second_page.json()["total"] == 2
    assert second_page.json()["items"][0]["id"] != payload["items"][0]["id"]
    assert client.get(
        "/api/v1/admin/users",
        params={"page_size": 101},
        headers=headers,
    ).status_code == 422


def test_admin_can_create_standard_user_account_that_can_sign_in(client, db, monkeypatch):
    _configure_admin_owner(monkeypatch, "owner@example.com")
    admin = _create_admin(db, "owner@example.com", "OwnerPassword123")
    headers = {"Authorization": f"Bearer {_login(client, admin.email, 'OwnerPassword123')}"}
    response = client.post(
        "/api/v1/admin/users",
        json={
            "full_name": "Created User",
            "email": "created@example.com",
            "password": "CreatedUser123",
        },
        headers=headers,
    )

    assert response.status_code == 201
    created = response.json()
    assert created["full_name"] == "Created User"
    assert created["email"] == "created@example.com"
    assert created["role"] == "user"
    assert created["is_active"] is True
    assert "hashed_password" not in created
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "created@example.com", "password": "CreatedUser123"},
    ).status_code == 200
    assert client.post(
        "/api/v1/admin/users",
        json={
            "full_name": "Duplicate User",
            "email": "created@example.com",
            "password": "AnotherUser123",
        },
        headers=headers,
    ).status_code == 409
    assert client.post(
        "/api/v1/admin/users",
        json={
            "full_name": "Privilege Escalation",
            "email": "escalation@example.com",
            "password": "Escalation123",
            "role": "admin",
        },
        headers=headers,
    ).status_code == 422


def test_admin_can_deactivate_and_reactivate_standard_accounts_only(client, db, monkeypatch):
    _configure_admin_owner(monkeypatch, "owner@example.com")
    admin = _create_admin(db, "owner@example.com", "OwnerPassword123")
    target = User(
        full_name="Managed User",
        email="managed@example.com",
        hashed_password=hash_password("ManagedPassword123"),
        role="user",
        is_active=True,
    )
    other_admin = User(
        full_name="Other Admin",
        email="other-admin@example.com",
        hashed_password=hash_password("OtherAdminPassword123"),
        role="admin",
        is_active=True,
    )
    db.add_all([target, other_admin])
    db.commit()
    headers = {"Authorization": f"Bearer {_login(client, admin.email, 'OwnerPassword123')}"}

    deactivated = client.patch(
        f"/api/v1/admin/users/{target.id}/status",
        json={"is_active": False},
        headers=headers,
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert "hashed_password" not in deactivated.json()
    assert client.post(
        "/api/v1/auth/login",
        json={"email": target.email, "password": "ManagedPassword123"},
    ).status_code == 401

    reactivated = client.patch(
        f"/api/v1/admin/users/{target.id}/status",
        json={"is_active": True},
        headers=headers,
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True
    assert client.post(
        "/api/v1/auth/login",
        json={"email": target.email, "password": "ManagedPassword123"},
    ).status_code == 200

    assert client.patch(
        f"/api/v1/admin/users/{admin.id}/status",
        json={"is_active": False},
        headers=headers,
    ).status_code == 409
    assert client.patch(
        f"/api/v1/admin/users/{other_admin.id}/status",
        json={"is_active": False},
        headers=headers,
    ).status_code == 409
    assert client.patch(
        "/api/v1/admin/users/999999/status",
        json={"is_active": False},
        headers=headers,
    ).status_code == 404
    assert client.patch(
        f"/api/v1/admin/users/{target.id}/status",
        json={"is_active": "false"},
        headers=headers,
    ).status_code == 422


def test_all_admin_routes_require_owner_authorization(client, db, monkeypatch):
    _configure_admin_owner(monkeypatch, "owner@example.com")
    admin = _create_admin(db, "owner@example.com", "OwnerPassword123")
    owner_headers = {"Authorization": f"Bearer {_login(client, admin.email, 'OwnerPassword123')}"}
    normal_user = User(
        full_name="Normal User",
        email="normal-admin-test@example.com",
        hashed_password=hash_password("NormalPassword123"),
        role="user",
        is_active=True,
    )
    db.add(normal_user)
    other_admin = User(
        full_name="Different Admin",
        email="different-admin@example.com",
        hashed_password=hash_password("DifferentAdmin123"),
        role="admin",
        is_active=True,
    )
    db.add(other_admin)
    db.commit()
    user_headers = {"Authorization": f"Bearer {_login(client, normal_user.email, 'NormalPassword123')}"}
    other_admin_headers = {
        "Authorization": f"Bearer {_login(client, other_admin.email, 'DifferentAdmin123')}"
    }
    routes = [
        ("post", "/api/v1/admin/users", {
            "full_name": "Authorized Created User",
            "email": "created-by-admin@example.com",
            "password": "CreatedByAdmin123",
        }),
        ("get", "/api/v1/admin/users", None),
        ("get", "/api/v1/admin/health", None),
        ("patch", f"/api/v1/admin/users/{normal_user.id}/status", {"is_active": True}),
    ]
    for method, path, body in routes:
        request = getattr(client, method)
        kwargs = {"headers": owner_headers}
        if body is not None:
            kwargs["json"] = body
        expected = 201 if method == "post" else 200
        assert request(path, **kwargs).status_code == expected

        kwargs["headers"] = user_headers
        assert request(path, **kwargs).status_code == 403
        kwargs["headers"] = other_admin_headers
        assert request(path, **kwargs).status_code == 403
        kwargs.pop("headers")
        assert request(path, **kwargs).status_code == 401


def test_admin_health_reports_database_failure_without_leaking_details(client, db, monkeypatch):
    from sqlalchemy.exc import OperationalError

    _configure_admin_owner(monkeypatch, "owner@example.com")
    admin = _create_admin(db, "owner@example.com", "OwnerPassword123")
    headers = {"Authorization": f"Bearer {_login(client, admin.email, 'OwnerPassword123')}"}
    response = client.get("/api/v1/admin/health", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["database"] == "available"

    original_execute = db.execute

    def fail_health_query(statement, *args, **kwargs):
        if str(statement) == "SELECT 1":
            raise OperationalError("SELECT 1", {}, Exception("sensitive connection detail"))
        return original_execute(statement, *args, **kwargs)

    monkeypatch.setattr(db, "execute", fail_health_query)
    failed = client.get("/api/v1/admin/health", headers=headers)
    assert failed.status_code == 503
    assert failed.json()["detail"] == "Database health check failed"
    assert "sensitive connection detail" not in failed.text

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.config import get_settings
from backend.database import Base
from backend.dependencies import get_current_admin, get_db, get_current_user
from backend.main import app
from backend.models import User
from backend.security import create_access_token, hash_password, verify_password


TEST_ENGINE = create_engine(
	"sqlite://",
	connect_args={"check_same_thread": False},
	poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=TEST_ENGINE, autoflush=False, autocommit=False)
Base.metadata.create_all(bind=TEST_ENGINE)


def override_get_db():
	db = TestSessionLocal()
	try:
		yield db
	finally:
		db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_database():
	app.dependency_overrides[get_db] = override_get_db
	Base.metadata.drop_all(bind=TEST_ENGINE)
	Base.metadata.create_all(bind=TEST_ENGINE)
	yield
	app.dependency_overrides.pop(get_db, None)


def register_user(email="amina@example.com"):
	return client.post(
		"/api/v1/auth/register",
		json={"full_name": "Amina Otieno", "email": email, "password": "Secure123"},
	)


def test_valid_registration_hashes_password_and_returns_safe_profile():
	response = register_user()

	assert response.status_code == 201
	body = response.json()
	assert body["email"] == "amina@example.com"
	assert "password" not in body
	assert "hashed_password" not in body

	db = TestSessionLocal()
	user = db.query(User).filter(User.email == "amina@example.com").one()
	assert user.hashed_password != "Secure123"
	assert verify_password("Secure123", user.hashed_password)
	db.close()


def test_duplicate_email_is_rejected():
	assert register_user().status_code == 201
	assert register_user().status_code == 409


def test_invalid_registration_data_is_rejected():
	assert register_user("bad-email").status_code == 422
	response = client.post(
		"/api/v1/auth/register",
		json={"full_name": "Amina", "email": "amina2@example.com", "password": "short"},
	)
	assert response.status_code == 422


def test_login_success_and_auth_me():
	register_user()
	response = client.post(
		"/api/v1/auth/login",
		json={"email": "AMINA@example.com", "password": "Secure123"},
	)

	assert response.status_code == 200
	token = response.json()["access_token"]
	assert response.json()["token_type"] == "bearer"
	me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
	assert me.status_code == 200
	assert me.json()["email"] == "amina@example.com"
	assert "hashed_password" not in me.json()


def test_invalid_login_does_not_reveal_account_state():
	register_user()
	wrong_password = client.post(
		"/api/v1/auth/login",
		json={"email": "amina@example.com", "password": "Wrong123"},
	)
	missing_user = client.post(
		"/api/v1/auth/login",
		json={"email": "missing@example.com", "password": "Wrong123"},
	)
	assert wrong_password.status_code == missing_user.status_code == 401
	assert wrong_password.json() == missing_user.json()


def test_inactive_user_cannot_login():
	register_user()
	db = TestSessionLocal()
	db.query(User).filter(User.email == "amina@example.com").update({"is_active": False})
	db.commit()
	db.close()
	response = client.post(
		"/api/v1/auth/login",
		json={"email": "amina@example.com", "password": "Secure123"},
	)
	assert response.status_code == 401


def test_missing_malformed_and_expired_tokens_are_rejected():
	assert client.get("/api/v1/auth/me").status_code == 401
	assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer malformed"}).status_code == 401
	expired = jwt.encode(
		{"sub": "1", "role": "user", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
		get_settings().SECRET_KEY,
		algorithm=get_settings().ALGORITHM,
	)
	assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_admin_dependency_rejects_users_and_accepts_admins():
	user = User(id=1, full_name="User", email="user@example.com", hashed_password="hash", role="user")
	with pytest.raises(HTTPException) as error:
		get_current_admin(user)
	assert error.value.status_code == 403

	admin = User(id=2, full_name="Admin", email="admin@example.com", hashed_password="hash", role="admin")
	assert get_current_admin(admin) is admin


def test_jwt_contains_only_minimal_identity_claims():
	token = create_access_token("42", "user")
	payload = jwt.decode(token, get_settings().SECRET_KEY, algorithms=[get_settings().ALGORITHM])
	assert payload["sub"] == "42"
	assert payload["role"] == "user"
	assert set(payload) == {"sub", "role", "iat", "exp"}

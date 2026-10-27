from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.config import get_settings
from backend.database import Base
from backend.dependencies import get_current_admin, get_db
from backend.main import app
from backend.models import User
from backend.routes import auth as auth_routes
from backend.security import create_access_token, verify_password
from backend.services import email_service
from backend.services.auth_service import create_password_reset_token


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


def test_public_registration_rejects_forged_admin_role_and_still_creates_users():
	forged = client.post(
		"/api/v1/auth/register",
		json={
			"full_name": "Forged Admin",
			"email": "forged-admin@example.com",
			"password": "ForgedAdmin123",
			"role": "admin",
		},
	)
	assert forged.status_code == 422

	assert register_user("ordinary@example.com").status_code == 201
	db = TestSessionLocal()
	ordinary = db.query(User).filter(User.email == "ordinary@example.com").one()
	assert ordinary.role == "user"
	db.close()


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


def test_admin_dependency_accepts_active_admins_and_rejects_normal_users(monkeypatch):
	monkeypatch.setattr(
		"backend.dependencies.get_settings",
		lambda: SimpleNamespace(ADMIN_OWNER_EMAIL="admin@example.com"),
	)
	user = User(id=1, full_name="User", email="user@example.com", hashed_password="hash", role="user")
	with pytest.raises(HTTPException) as error:
		get_current_admin(user)
	assert error.value.status_code == 403

	admin = User(id=2, full_name="Admin", email="admin@example.com", hashed_password="hash", role="admin")
	assert get_current_admin(admin) is admin
	other_admin = User(id=3, full_name="Other Admin", email="other@example.com", hashed_password="hash", role="admin")
	assert get_current_admin(other_admin) is other_admin


def test_jwt_contains_only_minimal_identity_claims():
	token = create_access_token("42", "user")
	payload = jwt.decode(token, get_settings().SECRET_KEY, algorithms=[get_settings().ALGORITHM])
	assert payload["sub"] == "42"
	assert payload["role"] == "user"
	assert set(payload) == {"sub", "role", "iat", "exp"}


def get_password_reset_token(email="amina@example.com"):
	register_user(email)
	db = TestSessionLocal()
	user = db.query(User).filter(User.email == email).one()
	token = create_password_reset_token(user)
	db.close()
	return token


def test_forgot_password_sends_reset_email_when_smtp_is_configured(monkeypatch):
	emails = []
	monkeypatch.setattr(auth_routes, "password_reset_email_configured", lambda: True)
	monkeypatch.setattr(auth_routes, "send_password_reset_email", lambda recipient, url: emails.append((recipient, url)))
	register_user()

	response = client.post("/api/v1/auth/forgot-password", json={"email": "amina@example.com"})

	assert response.status_code == 202
	assert response.json() == {"message": "If an account exists for that email, a password reset link will be sent shortly."}
	assert emails[0][0] == "amina@example.com"
	assert emails[0][1].startswith(f"{get_settings().FRONTEND_URL}/reset-password#token=")
	assert "#token=" in emails[0][1]


def test_forgot_password_returns_explicit_unavailable_error_without_smtp(monkeypatch):
	monkeypatch.setattr(auth_routes, "password_reset_email_configured", lambda: False)
	register_user()

	response = client.post("/api/v1/auth/forgot-password", json={"email": "amina@example.com"})

	assert response.status_code == 503
	assert response.json() == {"detail": "Password reset is temporarily unavailable."}


def test_forgot_password_uses_same_response_for_existing_and_missing_email(monkeypatch):
	emails = []
	monkeypatch.setattr(auth_routes, "password_reset_email_configured", lambda: True)
	monkeypatch.setattr(auth_routes, "send_password_reset_email", lambda recipient, url: emails.append((recipient, url)))
	register_user()

	existing = client.post("/api/v1/auth/forgot-password", json={"email": "amina@example.com"})
	missing = client.post("/api/v1/auth/forgot-password", json={"email": "missing@example.com"})

	assert existing.status_code == missing.status_code == 202
	assert existing.json() == missing.json()
	assert [email for email, _url in emails] == ["amina@example.com", "missing@example.com"]
	assert emails[0][1].startswith(f"{get_settings().FRONTEND_URL}/reset-password#token=")
	assert emails[1][1] is None


def test_inactive_and_missing_users_receive_generic_no_link_notice(monkeypatch):
	emails = []
	monkeypatch.setattr(auth_routes, "password_reset_email_configured", lambda: True)
	monkeypatch.setattr(auth_routes, "send_password_reset_email", lambda recipient, url: emails.append((recipient, url)))
	register_user()
	db = TestSessionLocal()
	db.query(User).filter(User.email == "amina@example.com").update({"is_active": False})
	db.commit()
	db.close()

	inactive = client.post("/api/v1/auth/forgot-password", json={"email": "amina@example.com"})
	missing = client.post("/api/v1/auth/forgot-password", json={"email": "missing@example.com"})

	assert inactive.status_code == missing.status_code == 202
	assert emails == [
		("amina@example.com", None),
		("missing@example.com", None),
	]


def test_password_reset_delivery_failure_is_account_enumeration_safe(monkeypatch):
	monkeypatch.setattr(auth_routes, "password_reset_email_configured", lambda: True)

	def fail_delivery(_recipient, _url):
		raise RuntimeError("SMTP failure")

	monkeypatch.setattr(auth_routes, "send_password_reset_email", fail_delivery)
	register_user()

	existing = client.post("/api/v1/auth/forgot-password", json={"email": "amina@example.com"})
	missing = client.post("/api/v1/auth/forgot-password", json={"email": "missing@example.com"})

	assert existing.status_code == missing.status_code == 503
	assert existing.json() == missing.json() == {
		"detail": "Password reset is temporarily unavailable."
	}


def test_valid_password_reset_token_is_accepted():
	token = get_password_reset_token()

	response = client.post("/api/v1/auth/reset-password/validate", json={"token": token})

	assert response.status_code == 200
	assert response.json() == {"valid": True}


def test_invalid_password_reset_token_is_rejected():
	response = client.post("/api/v1/auth/reset-password/validate", json={"token": "invalid-token"})

	assert response.status_code == 400


def test_expired_password_reset_token_is_rejected():
	token = get_password_reset_token()
	payload = jwt.decode(token, get_settings().SECRET_KEY, algorithms=[get_settings().ALGORITHM])
	payload["exp"] = datetime.now(timezone.utc) - timedelta(minutes=1)
	expired_token = jwt.encode(payload, get_settings().SECRET_KEY, algorithm=get_settings().ALGORITHM)

	response = client.post("/api/v1/auth/reset-password/validate", json={"token": expired_token})

	assert response.status_code == 400


def test_successful_password_reset_invalidates_old_password_and_token():
	register_user()
	db = TestSessionLocal()
	user = db.query(User).filter(User.email == "amina@example.com").one()
	token = create_password_reset_token(user)
	db.close()

	reset = client.post(
		"/api/v1/auth/reset-password",
		json={"token": token, "password": "NewSecure456"},
	)
	old_password = client.post(
		"/api/v1/auth/login",
		json={"email": "amina@example.com", "password": "Secure123"},
	)
	new_password = client.post(
		"/api/v1/auth/login",
		json={"email": "amina@example.com", "password": "NewSecure456"},
	)
	used_token = client.post("/api/v1/auth/reset-password/validate", json={"token": token})

	assert reset.status_code == 200
	assert old_password.status_code == 401
	assert new_password.status_code == 200
	assert used_token.status_code == 400


def test_weak_reset_password_is_rejected():
	token = get_password_reset_token()

	response = client.post(
		"/api/v1/auth/reset-password",
		json={"token": token, "password": "12345678"},
	)

	assert response.status_code == 422


def test_smtp_delivery_failure_returns_503(monkeypatch):
	monkeypatch.setattr(auth_routes, "password_reset_email_configured", lambda: True)
	monkeypatch.setattr(
		auth_routes,
		"send_password_reset_email",
		lambda recipient, url: (_ for _ in ()).throw(RuntimeError("delivery failed")),
	)
	register_user()

	response = client.post("/api/v1/auth/forgot-password", json={"email": "amina@example.com"})

	assert response.status_code == 503


def test_smtp_delivery_uses_settings_without_hardcoded_credentials(monkeypatch):
	settings = SimpleNamespace(
		SMTP_HOST="smtp.test.invalid",
		SMTP_PORT=2525,
		SMTP_USERNAME="smtp-user",
		SMTP_PASSWORD="smtp-password",
		SMTP_FROM_EMAIL="no-reply@test.invalid",
		SMTP_USE_TLS=False,
	)
	connections = []

	class FakeSMTP:
		def __init__(self, host, port, timeout):
			connections.append(self)
			self.host = host
			self.port = port
			self.timeout = timeout
			self.login_args = None
			self.message = None

		def __enter__(self):
			return self

		def __exit__(self, exc_type, exc_value, traceback):
			return False

		def login(self, username, password):
			self.login_args = (username, password)

		def send_message(self, message):
			self.message = message

	monkeypatch.setattr(email_service, "get_settings", lambda: settings)
	monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)

	email_service.send_password_reset_email("recipient@test.invalid", "https://test.invalid/reset")

	assert email_service.password_reset_email_configured() is True
	assert connections[0].host == settings.SMTP_HOST
	assert connections[0].login_args == (settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
	assert connections[0].message["From"] == settings.SMTP_FROM_EMAIL

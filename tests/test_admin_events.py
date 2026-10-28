from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import dependencies, security
from backend.database import Base
from backend.dependencies import get_db
from backend.main import app
from backend.models import AdminAuditLog, Assessment, OperationalEvent, User
from backend.security import create_access_token, hash_password


TEST_ENGINE = create_engine(
	"sqlite://",
	connect_args={"check_same_thread": False},
	poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=TEST_ENGINE, autoflush=False, autocommit=False)


@pytest.fixture()
def db():
	Base.metadata.drop_all(bind=TEST_ENGINE)
	Base.metadata.create_all(bind=TEST_ENGINE)
	session = TestSessionLocal()
	try:
		yield session
	finally:
		session.close()


@pytest.fixture()
def client(db, monkeypatch):
	settings = SimpleNamespace(
		ADMIN_OWNER_EMAIL="admin@example.com",
		SECRET_KEY="admin-events-tests-secret-key-0123456789",
		ALGORITHM="HS256",
		ACCESS_TOKEN_EXPIRE_MINUTES=30,
	)
	monkeypatch.setattr(dependencies, "get_settings", lambda: settings)
	monkeypatch.setattr(security, "get_settings", lambda: settings)

	def override_get_db():
		yield db

	app.dependency_overrides[get_db] = override_get_db
	try:
		yield TestClient(app)
	finally:
		app.dependency_overrides.pop(get_db, None)


def create_user(db, email, role="user", is_active=True):
	user = User(
		full_name=email.split("@")[0],
		email=email,
		hashed_password=hash_password("TestPassword123"),
		role=role,
		is_active=is_active,
	)
	db.add(user)
	db.flush()
	return user


def auth_headers(user, role):
	token = create_access_token(str(user.id), role)
	return {"Authorization": f"Bearer {token}"}


def test_admin_event_views_are_protected(client, db):
	user = create_user(db, "member@example.com")
	admin = create_user(db, "admin@example.com", role="admin")
	db.commit()
	for path in (
		"/api/v1/admin/audit-logs",
		"/api/v1/admin/operational-events",
		"/api/v1/admin/alerts",
		"/api/v1/admin/operational-summary",
	):
		assert client.get(path).status_code == 401
		assert client.get(path, headers=auth_headers(user, "user")).status_code == 403
		assert client.get(path, headers=auth_headers(admin, "admin")).status_code == 200
	assert client.post(
		"/api/v1/admin/alerts/999/acknowledge"
	).status_code == 401
	assert client.post(
		"/api/v1/admin/alerts/999/acknowledge",
		headers=auth_headers(user, "user"),
	).status_code == 403
	assert client.post(
		"/api/v1/admin/alerts/999/acknowledge",
		headers=auth_headers(admin, "admin"),
	).status_code == 404
	assert client.put(
		"/api/v1/admin/audit-logs", headers=auth_headers(admin, "admin")
	).status_code == 405
	assert client.delete(
		"/api/v1/admin/audit-logs", headers=auth_headers(admin, "admin")
	).status_code == 405


def test_operational_events_filter_paginate_and_acknowledge_with_audit(
	client, db
):
	admin = create_user(db, "admin@example.com", role="admin")
	now = datetime.now(timezone.utc)
	first = OperationalEvent(
		event_type="prediction.unavailable",
		source="prediction",
		severity="error",
		summary="Safe service failure summary.",
		status="open",
		occurred_at=now,
	)
	second = OperationalEvent(
		event_type="prediction.generation_failed",
		source="prediction",
		severity="error",
		summary="Another safe failure summary.",
		status="open",
		occurred_at=now,
	)
	informational = OperationalEvent(
		event_type="health.checked",
		source="health",
		severity="info",
		summary="Informational event.",
		status="open",
		occurred_at=now,
	)
	db.add_all([first, second, informational])
	db.commit()
	headers = auth_headers(admin, "admin")

	page = client.get(
		"/api/v1/admin/operational-events",
		params={"page": 2, "page_size": 1, "status_filter": "open"},
		headers=headers,
	)
	alerts = client.get("/api/v1/admin/alerts", headers=headers)
	error_events = client.get(
		"/api/v1/admin/operational-events",
		params={"severity_filter": "error"},
		headers=headers,
	)
	summary = client.get("/api/v1/admin/operational-summary", headers=headers)
	assert page.status_code == alerts.status_code == error_events.status_code == summary.status_code == 200
	assert page.json()["total"] == 3
	assert len(page.json()["items"]) == 1
	assert len(alerts.json()["items"]) == 2
	assert error_events.json()["total"] == 2
	assert summary.json()["recorded_error_count"] == 2
	assert summary.json()["open_alert_count"] == 2
	assert "details" not in alerts.json()["items"][0]

	acknowledged = client.post(
		f"/api/v1/admin/alerts/{first.id}/acknowledge",
		headers=headers,
	)
	assert acknowledged.status_code == 200
	assert acknowledged.json()["status"] == "acknowledged"
	assert acknowledged.json()["acknowledged_by_user_id"] == admin.id
	assert acknowledged.json()["acknowledged_at"] is not None
	assert client.post(
		f"/api/v1/admin/alerts/{first.id}/acknowledge",
		headers=headers,
	).status_code == 409
	updated_summary = client.get("/api/v1/admin/operational-summary", headers=headers)
	assert updated_summary.json()["recorded_error_count"] == 2
	assert updated_summary.json()["open_alert_count"] == 1
	audit = client.get("/api/v1/admin/audit-logs", headers=headers)
	assert audit.json()["total"] == 2
	audit_by_action = {item["action"]: item for item in audit.json()["items"]}
	assert audit_by_action["operational_event.acknowledged"]["outcome"] == "success"
	assert audit_by_action["operational_event.acknowledged"]["actor_user_id"] == admin.id
	assert audit_by_action["operational_event.acknowledgement_rejected"]["outcome"] == "failure"
	assert audit_by_action["operational_event.acknowledgement_rejected"]["actor_user_id"] == admin.id
	assert client.post(
		f"/api/v1/admin/alerts/{informational.id}/acknowledge",
		headers=headers,
	).status_code == 409
	invalid_attempt = client.get(
		"/api/v1/admin/audit-logs",
		params={"action": "operational_event.acknowledgement_rejected"},
		headers=headers,
	)
	assert invalid_attempt.json()["total"] == 2
	assert {item["target_id"] for item in invalid_attempt.json()["items"]} == {
		str(first.id), str(informational.id)
	}
	missing = client.post(
		"/api/v1/admin/alerts/999/acknowledge",
		headers=headers,
	)
	assert missing.status_code == 404
	missing_attempt = client.get(
		"/api/v1/admin/audit-logs",
		params={"action": "operational_event.acknowledgement_rejected"},
		headers=headers,
	)
	assert missing_attempt.json()["total"] == 3
	assert missing_attempt.json()["items"][0]["target_id"] == "999"
	acknowledged_events = client.get(
		"/api/v1/admin/operational-events",
		params={"status_filter": "acknowledged"},
		headers=headers,
	)
	assert acknowledged_events.status_code == 200
	assert acknowledged_events.json()["total"] == 1


def test_admin_audit_log_filters_and_outcome_values(client, db):
	admin = create_user(db, "admin@example.com", role="admin")
	now = datetime.now(timezone.utc)
	db.add_all([
		AdminAuditLog(
			actor_user_id=admin.id, action="user.deactivated", target_type="user",
			target_id="42", outcome="success", created_at=now,
		),
		AdminAuditLog(
			actor_user_id=admin.id, action="user.status_change_rejected",
			target_type="user", target_id="43", outcome="failure",
			created_at=now,
		),
		AdminAuditLog(
			actor_user_id=None, action="legacy.action", outcome="unknown",
			created_at=now,
		),
	])
	db.commit()
	headers = auth_headers(admin, "admin")

	response = client.get(
		"/api/v1/admin/audit-logs",
		params={
			"action": "user.status_change_rejected",
			"actor_user_id": admin.id,
			"outcome": "failure",
			"created_after": (now - timedelta(minutes=1)).isoformat(),
			"created_before": (now + timedelta(minutes=1)).isoformat(),
		},
		headers=headers,
	)
	assert response.status_code == 200
	assert response.json()["total"] == 1
	assert response.json()["items"][0]["outcome"] == "failure"
	assert response.json()["items"][0]["target_id"] == "43"
	assert client.get(
		"/api/v1/admin/audit-logs",
		params={"outcome": "unknown"},
		headers=headers,
	).json()["items"][0]["action"] == "legacy.action"
	assert client.get(
		"/api/v1/admin/audit-logs",
		params={
			"created_after": (now + timedelta(days=1)).isoformat(),
			"created_before": now.isoformat(),
		},
		headers=headers,
	).status_code == 422
	assert client.get(
		"/api/v1/admin/audit-logs",
		params={"outcome": "resolved"},
		headers=headers,
	).status_code == 422
	assert client.get(
		"/api/v1/admin/operational-events",
		params={"severity_filter": "resolved"},
		headers=headers,
	).status_code == 422


def test_admin_user_status_change_is_audited(client, db):
	admin = create_user(db, "admin@example.com", role="admin")
	member = create_user(db, "member@example.com")
	db.commit()

	response = client.patch(
		f"/api/v1/admin/users/{member.id}/status",
		json={"is_active": False},
		headers=auth_headers(admin, "admin"),
	)
	assert response.status_code == 200
	audit = client.get(
		"/api/v1/admin/audit-logs",
		headers=auth_headers(admin, "admin"),
	)
	assert audit.status_code == 200
	assert audit.json()["total"] == 1
	assert audit.json()["items"][0]["actor_user_id"] == admin.id
	assert audit.json()["items"][0]["action"] == "user.deactivated"
	assert audit.json()["items"][0]["outcome"] == "success"
	assert audit.json()["items"][0]["target_id"] == str(member.id)


def test_rejected_admin_account_actions_are_audited_without_submitted_details(
	client, db
):
	admin = create_user(db, "admin@example.com", role="admin")
	other_admin = create_user(db, "other-admin@example.com", role="admin")
	db.commit()
	headers = auth_headers(admin, "admin")

	create_response = client.post(
		"/api/v1/admin/admins",
		json={
			"full_name": "Attempted Admin",
			"email": "attempted-admin@example.com",
			"password": "SensitivePassword123",
		},
		headers=headers,
	)
	status_response = client.patch(
		f"/api/v1/admin/users/{other_admin.id}/status",
		json={"is_active": False},
		headers=headers,
	)
	assert create_response.status_code == 409
	assert status_response.status_code == 409

	audit = client.get("/api/v1/admin/audit-logs", headers=headers)
	assert audit.status_code == 200
	assert audit.json()["total"] == 2
	entries = {entry["action"]: entry for entry in audit.json()["items"]}
	assert entries["admin.account_creation_rejected"]["actor_user_id"] == admin.id
	assert entries["admin.account_creation_rejected"]["outcome"] == "failure"
	assert entries["admin.account_creation_rejected"]["target_id"] is None
	assert entries["user.status_change_rejected"]["actor_user_id"] == admin.id
	assert entries["user.status_change_rejected"]["outcome"] == "failure"
	assert entries["user.status_change_rejected"]["target_id"] == str(other_admin.id)
	assert "attempted-admin@example.com" not in audit.text
	assert "SensitivePassword123" not in audit.text


def test_admin_standard_user_creation_rejection_is_audited_safely(client, db):
	admin = create_user(db, "admin@example.com", role="admin")
	create_user(db, "existing@example.com")
	db.commit()
	response = client.post(
		"/api/v1/admin/users",
		json={
			"full_name": "Existing Member",
			"email": "existing@example.com",
			"password": "SensitivePassword123",
		},
		headers=auth_headers(admin, "admin"),
	)
	assert response.status_code == 409

	audit = client.get(
		"/api/v1/admin/audit-logs",
		headers=auth_headers(admin, "admin"),
	)
	assert audit.status_code == 200
	entry = audit.json()["items"][0]
	assert entry["action"] == "user.creation_rejected"
	assert entry["outcome"] == "failure"
	assert entry["actor_user_id"] == admin.id
	assert entry["target_type"] == "user"
	assert entry["target_id"] is None
	assert "SensitivePassword123" not in audit.text
	assert "existing@example.com" not in audit.text


def test_successful_admin_user_creation_is_audited_with_success_outcome(client, db):
	admin = create_user(db, "admin@example.com", role="admin")
	db.commit()

	response = client.post(
		"/api/v1/admin/users",
		json={
			"full_name": "Created Member",
			"email": "created-member@example.com",
			"password": "SensitivePassword123",
		},
		headers=auth_headers(admin, "admin"),
	)
	assert response.status_code == 201

	audit = client.get(
		"/api/v1/admin/audit-logs",
		headers=auth_headers(admin, "admin"),
	)
	assert audit.status_code == 200
	assert audit.json()["total"] == 1
	entry = audit.json()["items"][0]
	assert entry["actor_user_id"] == admin.id
	assert entry["action"] == "user.created_by_admin"
	assert entry["outcome"] == "success"
	assert entry["target_type"] == "user"
	assert entry["target_id"] == str(response.json()["id"])
	assert "created-member@example.com" not in audit.text
	assert "SensitivePassword123" not in audit.text


def test_admin_second_account_creation_success_is_audited(client, db):
	admin = create_user(db, "admin@example.com", role="admin")
	db.commit()
	response = client.post(
		"/api/v1/admin/admins",
		json={
			"full_name": "Second Admin",
			"email": "second-admin@example.com",
			"password": "SecondAdmin123",
		},
		headers=auth_headers(admin, "admin"),
	)
	assert response.status_code == 201
	audit = client.get(
		"/api/v1/admin/audit-logs",
		headers=auth_headers(admin, "admin"),
	)
	assert audit.status_code == 200
	assert audit.json()["total"] == 1
	entry = audit.json()["items"][0]
	assert entry["action"] == "admin.account_created"
	assert entry["outcome"] == "success"
	assert entry["actor_user_id"] == admin.id
	assert entry["target_id"] == str(response.json()["id"])
	assert "SecondAdmin123" not in audit.text


def test_successful_admin_login_is_audited(client, db):
	admin = create_user(db, "admin@example.com", role="admin")
	db.commit()

	response = client.post(
		"/api/v1/auth/login",
		json={"email": "admin@example.com", "password": "TestPassword123"},
	)
	assert response.status_code == 200
	audit = client.get(
		"/api/v1/admin/audit-logs",
		headers=auth_headers(admin, "admin"),
	)
	assert audit.status_code == 200
	assert audit.json()["total"] == 1
	entry = audit.json()["items"][0]
	assert entry["action"] == "admin.login_succeeded"
	assert entry["outcome"] == "success"
	assert entry["actor_user_id"] == admin.id


def test_prediction_service_failure_records_only_a_safe_operational_summary(
	client, db, monkeypatch
):
	import backend.routes.prediction as prediction_route
	from backend.services.prediction_service import (
		PredictionService,
		PredictionUnavailableError,
	)

	class UnavailablePredictor:
		def predict(self, _model_input):
			raise PredictionUnavailableError("sensitive exception text must not persist")

	user = create_user(db, "member@example.com")
	admin = create_user(db, "admin@example.com", role="admin")
	assessment = Assessment(
		user_id=user.id,
		assessment_status="completed",
		assessment_data={"private_input": "private value"},
	)
	db.add(assessment)
	db.commit()
	monkeypatch.setattr(
		prediction_route,
		"prediction_service",
		PredictionService(UnavailablePredictor()),
	)

	response = client.post(
		"/api/v1/predictions",
		json={"assessment_id": assessment.id},
		headers=auth_headers(user, "user"),
	)
	assert response.status_code == 503
	events = client.get(
		"/api/v1/admin/operational-events",
		headers=auth_headers(admin, "admin"),
	)
	assert events.status_code == 200
	assert events.json()["total"] == 1
	event = events.json()["items"][0]
	assert event["event_type"] == "prediction.unavailable"
	assert event["summary"] == "The prediction service could not process a request."
	assert "sensitive exception text" not in events.text
	assert "private value" not in events.text

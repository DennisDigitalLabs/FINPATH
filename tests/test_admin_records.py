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
from backend.models import Assessment, Prediction, Recommendation, User
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
		SECRET_KEY="admin-records-tests-secret-key-0123456789",
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
		full_name=email.split("@")[0].replace("-", " ").title(),
		email=email,
		hashed_password=hash_password("TestPassword123"),
		role=role,
		is_active=is_active,
	)
	db.add(user)
	db.flush()
	return user


def auth_headers(user_id, role="admin"):
	token = create_access_token(str(user_id), role)
	return {"Authorization": f"Bearer {token}"}


def seed_records(db):
	user = create_user(db, "record-owner@example.com")
	inactive_user = create_user(db, "inactive-owner@example.com", is_active=False)
	admin = create_user(db, "admin@example.com", role="admin")
	now = datetime.now(timezone.utc)
	completed = Assessment(
		user_id=user.id,
		assessment_status="completed",
		assessment_data={"private_input": "must not appear in admin summary"},
		created_at=now,
		assessment_date=now,
	)
	draft = Assessment(
		user_id=inactive_user.id,
		assessment_status="draft",
		assessment_data={"private_input": "must not appear in admin summary"},
		created_at=now - timedelta(minutes=1),
		assessment_date=now - timedelta(minutes=1),
	)
	db.add_all([completed, draft])
	db.flush()
	high = Prediction(
		assessment_id=completed.id,
		risk_level="high",
		risk_category="financial_access",
		probability=0.8,
		confidence=0.9,
		explanation="private explanation not returned",
		contributing_factors={"private": "factor"},
		model_version="v1",
		prediction_timestamp=now,
		created_at=now,
	)
	low = Prediction(
		assessment_id=completed.id,
		risk_level="low",
		risk_category="financial_access",
		probability=0.2,
		confidence=0.8,
		explanation="private explanation not returned",
		contributing_factors={"private": "factor"},
		model_version="v1",
		prediction_timestamp=now - timedelta(minutes=1),
		created_at=now - timedelta(minutes=1),
	)
	db.add_all([high, low])
	db.flush()
	db.add_all([
		Recommendation(
			prediction_id=high.id,
			category="savings",
			recommendation_text="Review a suitable savings option.",
			priority=1,
			created_at=now,
		),
		Recommendation(
			prediction_id=low.id,
			category="budgeting",
			recommendation_text="Review a suitable budgeting option.",
			priority=2,
			created_at=now - timedelta(minutes=1),
		),
	])
	db.commit()
	return user, inactive_user, admin, completed, draft, high, low


def test_admin_record_endpoints_require_active_admin_authorization(client, db):
	normal_user = create_user(db, "normal@example.com")
	admin = create_user(db, "admin@example.com", role="admin")
	db.commit()
	assert client.get("/api/v1/admin/records/assessments").status_code == 401
	assert client.get(
		"/api/v1/admin/records/assessments", headers=auth_headers(normal_user.id, "user")
	).status_code == 403
	assert client.get(
		"/api/v1/admin/records/assessments", headers=auth_headers(admin.id)
	).status_code == 200


def test_admin_assessment_records_filter_search_and_paginate(client, db):
	_, _, admin, completed, _, _, _ = seed_records(db)
	response = client.get(
		"/api/v1/admin/records/assessments",
		params={"filter_value": "COMPLETED", "search": "record-owner", "page": 1, "page_size": 1},
		headers=auth_headers(admin.id),
	)

	assert response.status_code == 200
	payload = response.json()
	assert payload["record_type"] == "assessments"
	assert payload["total"] == 1
	assert payload["page"] == 1
	assert payload["page_size"] == 1
	assert payload["items"][0]["id"] == completed.id
	assert payload["items"][0]["status"] == "completed"
	assert "assessment_data" not in payload["items"][0]
	assert "private_input" not in response.text


def test_admin_prediction_records_filter_and_pagination_counts_match(client, db):
	_, _, admin, _, _, high, low = seed_records(db)
	first = client.get(
		"/api/v1/admin/records/predictions",
		params={"filter_value": "high", "page": 1, "page_size": 1},
		headers=auth_headers(admin.id),
	)
	second = client.get(
		"/api/v1/admin/records/predictions",
		params={"page": 2, "page_size": 1},
		headers=auth_headers(admin.id),
	)

	assert first.status_code == second.status_code == 200
	assert first.json()["total"] == 1
	assert first.json()["items"][0]["id"] == high.id
	assert second.json()["total"] == 2
	assert second.json()["items"][0]["id"] == low.id
	assert "explanation" not in first.json()["items"][0]
	assert "contributing_factors" not in first.json()["items"][0]


def test_admin_recommendation_records_search_filter_and_empty_state(client, db):
	_, _, admin, *_ = seed_records(db)
	listed = client.get(
		"/api/v1/admin/records/recommendations",
		params={"filter_value": "savings", "search": "suitable savings"},
		headers=auth_headers(admin.id),
	)
	empty = client.get(
		"/api/v1/admin/records/recommendations",
		params={"filter_value": "missing-category"},
		headers=auth_headers(admin.id),
	)

	assert listed.status_code == 200
	assert listed.json()["total"] == 1
	assert listed.json()["items"][0]["category"] == "savings"
	assert listed.json()["items"][0]["recommendation_text"] == "Review a suitable savings option."
	assert empty.status_code == 200
	assert empty.json()["items"] == []
	assert empty.json()["total"] == 0


def test_admin_user_status_filter_keeps_total_consistent_with_items(client, db):
	_, _, admin, *_ = seed_records(db)
	response = client.get(
		"/api/v1/admin/users",
		params={"is_active": "false", "page": 1, "page_size": 10},
		headers=auth_headers(admin.id),
	)

	assert response.status_code == 200
	assert response.json()["total"] == 1
	assert len(response.json()["items"]) == 1
	assert response.json()["items"][0]["is_active"] is False


def test_model_monitoring_is_admin_only_and_reports_recorded_coverage(
	client, db, monkeypatch
):
	import backend.routes.prediction as prediction_route

	_, _, admin, *_ = seed_records(db)
	monkeypatch.setattr(
		prediction_route,
		"prediction_service",
		SimpleNamespace(model_available=True, model_version="test-runtime"),
	)
	assert client.get("/api/v1/admin/model").status_code == 401
	response = client.get(
		"/api/v1/admin/model",
		headers=auth_headers(admin.id),
	)

	assert response.status_code == 200
	payload = response.json()
	assert payload["model_available"] is True
	assert payload["model_version"] == "test-runtime"
	assert payload["recorded_prediction_count"] == 2
	assert payload["recorded_model_versions"] == {"v1": 2}
	assert payload["explanation_available_count"] == 2
	assert payload["contributing_factors_available_count"] == 2
	assert "explanation" not in payload
	assert "contributing_factors" not in payload
	assert "private explanation" not in response.text


def test_model_monitoring_reports_unavailable_runtime_and_empty_history(
	client, db, monkeypatch
):
	import backend.routes.prediction as prediction_route

	admin = create_user(db, "admin@example.com", role="admin")
	db.commit()
	monkeypatch.setattr(
		prediction_route,
		"prediction_service",
		SimpleNamespace(model_available=False, model_version=None),
	)
	response = client.get(
		"/api/v1/admin/model",
		headers=auth_headers(admin.id),
	)

	assert response.status_code == 200
	assert response.json()["model_available"] is False
	assert response.json()["model_version"] is None
	assert response.json()["recorded_prediction_count"] == 0
	assert response.json()["recorded_model_versions"] == {}
	assert response.json()["explanation_available_count"] == 0
	assert response.json()["contributing_factors_available_count"] == 0

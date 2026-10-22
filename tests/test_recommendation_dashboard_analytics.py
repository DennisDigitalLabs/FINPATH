from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.dependencies import get_db
from backend.main import app
from backend.models import Assessment, Prediction, Recommendation, User


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


def register_and_login(email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Amina Otieno", "email": email, "password": "Secure123"},
    )
    assert registered.status_code == 201
    logged_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Secure123"},
    )
    assert logged_in.status_code == 200
    return logged_in.json()["access_token"]


def create_assessment(token: str, status: str = "completed") -> int:
    response = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {token}"},
        json={"assessment_data": {"feature": 1}, "assessment_status": status},
    )
    assert response.status_code == 201
    return response.json()["id"]


def seed_prediction_and_recommendation(assessment_id: int) -> tuple[int, int]:
    db = TestSessionLocal()
    now = datetime.now(timezone.utc)
    prediction = Prediction(
        assessment_id=assessment_id,
        risk_level="medium",
        risk_category="financial_access",
        probability=0.6,
        confidence=0.8,
        explanation="Stored test prediction.",
        contributing_factors={"feature": 1},
        model_version="test-model",
        prediction_timestamp=now,
        created_at=now,
    )
    db.add(prediction)
    db.flush()
    recommendation = Recommendation(
        prediction_id=prediction.id,
        category="financial literacy",
        recommendation_text="Review available financial education resources.",
        priority=1,
        created_at=now,
    )
    db.add(recommendation)
    db.commit()
    db.refresh(prediction)
    db.refresh(recommendation)
    ids = prediction.id, recommendation.id
    db.close()
    return ids


def seed_prediction(assessment_id: int) -> int:
    db = TestSessionLocal()
    now = datetime.now(timezone.utc)
    prediction = Prediction(
        assessment_id=assessment_id,
        risk_level="medium",
        risk_category="financial_access",
        probability=0.6,
        confidence=0.8,
        explanation="Stored test prediction.",
        contributing_factors={"feature": 1},
        model_version="test-model",
        prediction_timestamp=now,
        created_at=now,
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    prediction_id = prediction.id
    db.close()
    return prediction_id


def seed_recommendation(prediction_id: int, text: str) -> int:
    db = TestSessionLocal()
    recommendation = Recommendation(
        prediction_id=prediction_id,
        category="financial literacy",
        recommendation_text=text,
        priority=1,
        created_at=datetime.now(timezone.utc),
    )
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    recommendation_id = recommendation.id
    db.close()
    return recommendation_id


def test_recommendation_retrieval_and_ownership():
    owner_token = register_and_login("recommendation-owner@example.com")
    other_token = register_and_login("recommendation-other@example.com")
    assessment_id = create_assessment(owner_token)
    _, recommendation_id = seed_prediction_and_recommendation(assessment_id)

    listed = client.get(
        "/api/v1/recommendations",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert listed.status_code == 200
    assert listed.json()[0]["prediction_id"] is not None
    assert listed.json()[0]["id"] == recommendation_id
    assert listed.json()[0]["category"] == "financial literacy"

    fetched = client.get(
        f"/api/v1/recommendations/{recommendation_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert fetched.status_code == 200

    hidden = client.get(
        f"/api/v1/recommendations/{recommendation_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert hidden.status_code == 404
    assert client.get("/api/v1/recommendations").status_code == 401


def test_prediction_recommendations_are_scoped_and_empty_when_none_exist():
    token = register_and_login("prediction-recommendations@example.com")
    assessment_id = create_assessment(token)
    first_prediction_id = seed_prediction(assessment_id)
    second_prediction_id = seed_prediction(assessment_id)
    first_recommendation_id = seed_recommendation(first_prediction_id, "First prediction action.")
    second_recommendation_id = seed_recommendation(second_prediction_id, "Second prediction action.")
    headers = {"Authorization": f"Bearer {token}"}

    first = client.get(
        f"/api/v1/recommendations/by-prediction/{first_prediction_id}",
        headers=headers,
    )
    second = client.get(
        f"/api/v1/recommendations/by-prediction/{second_prediction_id}",
        headers=headers,
    )
    empty = client.get(
        f"/api/v1/recommendations/by-prediction/{seed_prediction(assessment_id)}",
        headers=headers,
    )

    assert first.status_code == 200
    assert [item["id"] for item in first.json()] == [first_recommendation_id]
    assert [item["prediction_id"] for item in first.json()] == [first_prediction_id]
    assert second.status_code == 200
    assert [item["id"] for item in second.json()] == [second_recommendation_id]
    assert [item["prediction_id"] for item in second.json()] == [second_prediction_id]
    assert empty.status_code == 200
    assert empty.json() == []


def test_prediction_recommendations_reject_unknown_and_other_users_predictions():
    owner_token = register_and_login("prediction-owner@example.com")
    other_token = register_and_login("prediction-other@example.com")
    owner_assessment_id = create_assessment(owner_token)
    owner_prediction_id = seed_prediction(owner_assessment_id)
    recommendation_id = seed_recommendation(owner_prediction_id, "Private prediction action.")
    other_headers = {"Authorization": f"Bearer {other_token}"}

    unknown = client.get(
        "/api/v1/recommendations/by-prediction/999999",
        headers=other_headers,
    )
    forbidden = client.get(
        f"/api/v1/recommendations/by-prediction/{owner_prediction_id}",
        headers=other_headers,
    )
    owner_result = client.get(
        f"/api/v1/recommendations/by-prediction/{owner_prediction_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert unknown.status_code == 404
    assert unknown.json()["detail"] == "Prediction not found"
    assert forbidden.status_code == 404
    assert forbidden.json()["detail"] == unknown.json()["detail"]
    assert owner_result.status_code == 200
    assert [item["id"] for item in owner_result.json()] == [recommendation_id]


def test_prediction_recommendations_require_authentication():
    assert client.get("/api/v1/recommendations/by-prediction/1").status_code == 401


def test_dashboard_returns_owned_data_and_null_without_prediction():
    token = register_and_login("dashboard@example.com")
    assessment_id = create_assessment(token)
    dashboard = client.get(
        "/api/v1/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["user"]["email"] == "dashboard@example.com"
    assert body["assessment_count"] == 1
    assert body["latest_assessment"]["id"] == assessment_id
    assert body["latest_prediction"] is None
    assert body["latest_recommendations"] == []


def test_dashboard_includes_latest_prediction_and_recommendations():
    token = register_and_login("dashboard-prediction@example.com")
    assessment_id = create_assessment(token)
    prediction_id, recommendation_id = seed_prediction_and_recommendation(assessment_id)

    body = client.get(
        "/api/v1/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert body["latest_prediction"]["id"] == prediction_id
    assert body["latest_recommendations"][0]["id"] == recommendation_id
    assert body["latest_prediction"]["probability"] == 0.6


def test_user_analytics_calculates_only_owned_records():
    token = register_and_login("analytics-owner@example.com")
    other_token = register_and_login("analytics-other@example.com")
    assessment_id = create_assessment(token)
    seed_prediction_and_recommendation(assessment_id)
    create_assessment(other_token, "draft")

    response = client.get(
        "/api/v1/analytics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "total_assessments": 1,
        "completed_assessments": 1,
        "assessment_status_distribution": {"completed": 1},
        "prediction_count": 1,
        "risk_level_distribution": {"medium": 1},
        "recommendation_count": 1,
    }


def test_admin_system_analytics_and_user_forbidden(monkeypatch):
    monkeypatch.setattr(
        "backend.dependencies.get_settings",
        lambda: SimpleNamespace(ADMIN_OWNER_EMAIL="admin-analytics@example.com"),
    )
    user_token = register_and_login("regular-analytics@example.com")
    admin_token = register_and_login("admin-analytics@example.com")
    db = TestSessionLocal()
    db.query(User).filter(User.email == "admin-analytics@example.com").update({"role": "admin"})
    db.commit()
    db.close()

    assert client.get(
        "/api/v1/analytics/system",
        headers={"Authorization": f"Bearer {user_token}"},
    ).status_code == 403
    response = client.get(
        "/api/v1/analytics/system",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["user_count"] == 2
    assert "email" not in response.json()
    assert "assessment_data" not in response.json()


def test_empty_analytics_are_zero_and_authentication_is_required():
    token = register_and_login("empty-analytics@example.com")
    response = client.get("/api/v1/analytics", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["total_assessments"] == 0
    assert body["prediction_count"] == 0
    assert body["recommendation_count"] == 0
    assert body["assessment_status_distribution"] == {}
    assert body["risk_level_distribution"] == {}
    assert client.get("/api/v1/dashboard").status_code == 401

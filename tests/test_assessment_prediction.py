from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.dependencies import get_db
from backend.main import app
from backend.schemas.prediction import PredictionCreate
from backend.routes import prediction as prediction_route
from backend.services.prediction_service import MLInputMapperAdapter


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
    original_service = prediction_route.prediction_service
    prediction_route.prediction_service = prediction_route.PredictionService()
    yield
    prediction_route.prediction_service = original_service
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


def create_assessment(token: str, status: str = "draft"):
    return client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {token}"},
        json={"assessment_data": {"future_feature": 1}, "assessment_status": status},
    )


def test_assessment_crud_and_user_scoped_list():
    token = register_and_login("owner@example.com")
    created = create_assessment(token)
    assert created.status_code == 201
    assessment_id = created.json()["id"]

    listed = client.get("/api/v1/assessments", headers={"Authorization": f"Bearer {token}"})
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [assessment_id]

    updated = client.put(
        f"/api/v1/assessments/{assessment_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"assessment_status": "completed", "assessment_data": {"score": 0.8}},
    )
    assert updated.status_code == 200
    assert updated.json()["assessment_status"] == "completed"

    fetched = client.get(
        f"/api/v1/assessments/{assessment_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fetched.status_code == 200
    assert fetched.json()["assessment_data"] == {"score": 0.8}

    deleted = client.delete(
        f"/api/v1/assessments/{assessment_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert deleted.status_code == 204
    assert client.get(
        f"/api/v1/assessments/{assessment_id}",
        headers={"Authorization": f"Bearer {token}"},
    ).status_code == 404


def test_assessment_requires_authentication_and_valid_status():
    assert client.post("/api/v1/assessments", json={"assessment_data": {}}).status_code == 401
    token = register_and_login("validation@example.com")
    response = create_assessment(token, "submitted")
    assert response.status_code == 422


def test_assessment_ownership_is_enforced():
    owner_token = register_and_login("first@example.com")
    other_token = register_and_login("second@example.com")
    assessment_id = create_assessment(owner_token).json()["id"]

    assert client.get(
        f"/api/v1/assessments/{assessment_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    ).status_code == 404
    assert client.put(
        f"/api/v1/assessments/{assessment_id}",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"assessment_data": {"attempt": "unauthorized"}},
    ).status_code == 404
    assert client.delete(
        f"/api/v1/assessments/{assessment_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    ).status_code == 404


def test_prediction_requires_completed_owned_assessment():
    token = register_and_login("predictor@example.com")
    assessment_id = create_assessment(token).json()["id"]
    response = client.post(
        "/api/v1/predictions",
        headers={"Authorization": f"Bearer {token}"},
        json={"assessment_id": assessment_id},
    )
    assert response.status_code == 409

    completed_id = create_assessment(token, "completed").json()["id"]
    unavailable = client.post(
        "/api/v1/predictions",
        headers={"Authorization": f"Bearer {token}"},
        json={"assessment_id": completed_id},
    )
    assert unavailable.status_code == 503
    assert "prediction service" in unavailable.json()["detail"].lower()


def test_prediction_for_other_users_assessment_is_hidden():
    owner_token = register_and_login("prediction-owner@example.com")
    other_token = register_and_login("prediction-other@example.com")
    assessment_id = create_assessment(owner_token, "completed").json()["id"]

    response = client.post(
        "/api/v1/predictions",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"assessment_id": assessment_id},
    )
    assert response.status_code == 404


def test_injected_ml_predictor_stores_and_retrieves_prediction():
    token = register_and_login("ml@example.com")
    assessment_id = create_assessment(token, "completed").json()["id"]

    class TestPredictor:
        def predict(self, assessment_data: dict) -> PredictionCreate:
            assert assessment_data == {"future_feature": 1}
            return {
                "assessment_id": assessment_id,
                "risk_level": "medium",
                "risk_category": "financial_access",
                "probability": 0.7,
                "confidence": 0.9,
                "explanation": "Injected test model output.",
                "contributing_factors": {"future_feature": 1},
                "model_version": "test-model",
                "recommendations": ["Review your financial priorities."],
            }

    prediction_route.prediction_service = prediction_route.PredictionService(TestPredictor())
    response = client.post(
        "/api/v1/predictions",
        headers={"Authorization": f"Bearer {token}"},
        json={"assessment_id": assessment_id},
    )
    assert response.status_code == 201
    prediction_id = response.json()["id"]
    assert response.json()["probability"] == 0.7

    fetched = client.get(
        f"/api/v1/predictions/{prediction_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fetched.status_code == 200
    assert fetched.json()["model_version"] == "test-model"

    retried = client.post(
        "/api/v1/predictions",
        headers={"Authorization": f"Bearer {token}"},
        json={"assessment_id": assessment_id},
    )
    assert retried.status_code == 201
    assert retried.json()["id"] == prediction_id

    listed = client.get(
        f"/api/v1/assessments/{assessment_id}/predictions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    recommendations = client.get(
        "/api/v1/recommendations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert recommendations.status_code == 200
    assert len(recommendations.json()) == 1


def test_browser_shaped_assessment_reaches_prediction_and_recommendations():
    token = register_and_login("browser-flow@example.com")
    browser_data = {
        "age_range": "18-24",
        "sex": "Female",
        "county": "Nairobi City",
        "education": "Secondary completed",
        "marital_status": "Single / Never Married",
        "savings_usage": "Yes",
        "emergency_savings": "No",
        "loan_usage": "No",
        "chama_usage": "No",
        "sacco_use": "No",
        "mobile_money_use": "No",
        "CountLivelihood": "1",
        "financial_literacy_score": "3",
    }
    created = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {token}"},
        json={"assessment_data": browser_data, "assessment_status": "completed"},
    )
    assert created.status_code == 201
    assessment_id = created.json()["id"]

    class BrowserPredictor:
        def predict(self, model_input: dict) -> dict:
            assert model_input["Loan_usage"] == 0
            assert model_input["mobile_money_use"] == 3
            assert model_input["S7_2"] == 4
            return {
                "risk_category": "Moderate Risk",
                "probability": 0.6,
                "confidence": 0.8,
                "explanation": "Browser-shaped assessment output.",
                "recommendations": ["Review your savings plan."],
                "model_version": "test-model",
            }

    prediction_route.prediction_service = prediction_route.PredictionService(
        BrowserPredictor(), MLInputMapperAdapter()
    )
    response = client.post(
        "/api/v1/predictions",
        headers={"Authorization": f"Bearer {token}"},
        json={"assessment_id": assessment_id},
    )
    assert response.status_code == 201
    prediction_id = response.json()["id"]
    assert client.get(
        f"/api/v1/predictions/{prediction_id}",
        headers={"Authorization": f"Bearer {token}"},
    ).status_code == 200
    recommendations = client.get(
        "/api/v1/recommendations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert recommendations.status_code == 200
    assert len(recommendations.json()) == 1


def test_prediction_endpoints_require_authentication():
    assert client.post("/api/v1/predictions", json={"assessment_id": 1}).status_code == 401
    assert client.get("/api/v1/predictions/1").status_code == 401
    assert client.get("/api/v1/assessments/1/predictions").status_code == 401

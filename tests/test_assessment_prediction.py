from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.dependencies import get_db
from backend.main import app
from backend.models import Prediction, Recommendation
from backend.schemas.prediction import PredictionCreate
from backend.routes import prediction as prediction_route
from backend.services.prediction_service import PredictionService, RealFinpathPredictor


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


def complete_ml_assessment_data(loan_usage: str, mobile_money_use: str) -> dict:
    data = {
        "age_range": "25-34",
        "sex": "Female",
        "county": "Nairobi City",
        "education": "Secondary completed",
        "marital_status": "Single / Never Married",
        "savings_usage": "Yes",
        "emergency_savings": "No",
        "loan_usage": loan_usage,
        "chama_usage": "No",
        "sacco_use": "Regular",
        "mobile_money_use": mobile_money_use,
        "CountLivelihood": "1",
        "financial_literacy_score": "3",
    }
    if loan_usage == "Yes":
        data.update({
            "loan_formal": "No",
            "loan_informal": "No",
            "digital_credit_usage": "No",
            "loan_app_2": "No",
            "loan_fuliza_2": "No",
            "defaulted": "No",
        })
    if mobile_money_use != "No":
        data["S7_2"] = "4"
    return data


def create_real_prediction(token: str, assessment_data: dict, monkeypatch):
    monkeypatch.setattr(
        prediction_route,
        "prediction_service",
        PredictionService(RealFinpathPredictor()),
    )
    assessment_response = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {token}"},
        json={"assessment_data": assessment_data, "assessment_status": "completed"},
    )
    assert assessment_response.status_code == 201
    return client.post(
        "/api/v1/predictions",
        headers={"Authorization": f"Bearer {token}"},
        json={"assessment_id": assessment_response.json()["id"]},
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


def test_assessment_creation_is_idempotent_per_user_and_request_key():
    token = register_and_login("idempotent@example.com")
    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": "f87410a6-f58e-4ea6-94a4-388cc167747d",
    }
    payload = {
        "assessment_data": {"age_range": "25-34"},
        "assessment_status": "completed",
    }

    first = client.post("/api/v1/assessments", headers=headers, json=payload)
    retried = client.post("/api/v1/assessments", headers=headers, json=payload)

    assert first.status_code == retried.status_code == 201
    assert retried.json()["id"] == first.json()["id"]
    assert len(client.get("/api/v1/assessments", headers={"Authorization": f"Bearer {token}"}).json()) == 1

    conflicting = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"assessment_data": {"age_range": "35-44"}, "assessment_status": "completed"},
    )
    assert conflicting.status_code == 409
    assert len(client.get("/api/v1/assessments", headers={"Authorization": f"Bearer {token}"}).json()) == 1


def test_assessment_idempotency_key_is_scoped_to_authenticated_user():
    owner_token = register_and_login("idempotency-owner@example.com")
    other_token = register_and_login("idempotency-other@example.com")
    key = "e8d928b3-fcdb-4c2a-a563-e953075e35ef"
    payload = {"assessment_data": {"age_range": "25-34"}, "assessment_status": "completed"}

    owner_assessment = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {owner_token}", "Idempotency-Key": key},
        json=payload,
    )
    other_assessment = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {other_token}", "Idempotency-Key": key},
        json=payload,
    )

    assert owner_assessment.status_code == other_assessment.status_code == 201
    assert owner_assessment.json()["id"] != other_assessment.json()["id"]


def test_assessment_rejects_malformed_idempotency_key():
    token = register_and_login("invalid-idempotency@example.com")
    response = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "not-a-uuid"},
        json={"assessment_data": {}, "assessment_status": "completed"},
    )

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


def test_prediction_requires_completed_assessment_and_rejects_incomplete_input():
    token = register_and_login("predictor@example.com")
    assessment_id = create_assessment(token).json()["id"]
    response = client.post(
        "/api/v1/predictions",
        headers={"Authorization": f"Bearer {token}"},
        json={"assessment_id": assessment_id},
    )
    assert response.status_code == 409

    completed_id = create_assessment(token, "completed").json()["id"]
    incomplete = client.post(
        "/api/v1/predictions",
        headers={"Authorization": f"Bearer {token}"},
        json={"assessment_id": completed_id},
    )
    assert incomplete.status_code == 409
    assert incomplete.json()["detail"] == "Invalid assessment data: Age range is required"


def test_valid_assessment_still_returns_503_when_model_is_unavailable():
    token = register_and_login("model-unavailable@example.com")
    assessment = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "assessment_data": complete_ml_assessment_data("No", "No"),
            "assessment_status": "completed",
        },
    )

    unavailable = client.post(
        "/api/v1/predictions",
        headers={"Authorization": f"Bearer {token}"},
        json={"assessment_id": assessment.json()["id"]},
    )

    assert unavailable.status_code == 503
    assert "prediction service" in unavailable.json()["detail"].lower()


def test_real_model_prediction_accepts_populated_conditional_fields(monkeypatch):
    token = register_and_login("conditional-yes@example.com")

    response = create_real_prediction(
        token,
        complete_ml_assessment_data("Yes", "Regular"),
        monkeypatch,
    )

    assert response.status_code == 201, response.json()
    assert response.json()["assessment_id"] > 0
    assert response.json()["model_version"]


def test_real_model_prediction_accepts_legitimately_omitted_conditional_fields(monkeypatch):
    token = register_and_login("conditional-no@example.com")

    response = create_real_prediction(
        token,
        complete_ml_assessment_data("No", "No"),
        monkeypatch,
    )

    assert response.status_code == 201, response.json()
    assert response.json()["assessment_id"] > 0


def test_real_model_prediction_is_persisted_and_retrievable_by_owner(monkeypatch):
    token = register_and_login("real-model-retrieval@example.com")
    generated = create_real_prediction(
        token,
        complete_ml_assessment_data("No", "No"),
        monkeypatch,
    )

    assert generated.status_code == 201, generated.json()
    generated_data = generated.json()
    prediction_id = generated_data["id"]
    assessment_id = generated_data["assessment_id"]
    assert isinstance(prediction_id, int) and prediction_id > 0
    assert {
        "id",
        "assessment_id",
        "risk_level",
        "risk_category",
        "probability",
        "confidence",
        "explanation",
        "contributing_factors",
        "model_version",
        "prediction_timestamp",
        "created_at",
    } <= generated_data.keys()

    db = TestSessionLocal()
    try:
        persisted = db.get(Prediction, prediction_id)
        assert persisted is not None
        assert persisted.assessment_id == assessment_id
        assert persisted.risk_level == generated_data["risk_level"]
        assert persisted.risk_category == generated_data["risk_category"]
        assert persisted.probability == generated_data["probability"]
        assert persisted.confidence == generated_data["confidence"]
        assert persisted.explanation == generated_data["explanation"]
        assert persisted.contributing_factors == generated_data["contributing_factors"]
        assert persisted.model_version == generated_data["model_version"]
    finally:
        db.close()

    user = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert user.status_code == 200

    assessment = client.get(
        f"/api/v1/assessments/{assessment_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert assessment.status_code == 200
    assert assessment.json()["user_id"] == user.json()["id"]
    assert assessment.json()["assessment_data"]["age_range"] == "25-34"

    retrieved = client.get(
        f"/api/v1/predictions/{prediction_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert retrieved.status_code == 200
    assert retrieved.json() == generated_data
    assert retrieved.json()["id"] == prediction_id
    assert retrieved.json()["assessment_id"] == assessment_id

    recommendation_response = client.get(
        f"/api/v1/recommendations/by-prediction/{prediction_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert recommendation_response.status_code == 200
    recommendations = recommendation_response.json()
    assert recommendations
    assert all(item["prediction_id"] == prediction_id for item in recommendations)

    db = TestSessionLocal()
    try:
        persisted_recommendations = (
            db.query(Recommendation)
            .filter(Recommendation.prediction_id == prediction_id)
            .all()
        )
        assert {item.id for item in persisted_recommendations} == {
            item["id"] for item in recommendations
        }
    finally:
        db.close()


def test_real_mapper_rejects_missing_required_assessment_data_with_409(monkeypatch):
    token = register_and_login("conditional-incomplete@example.com")
    assessment_data = complete_ml_assessment_data("No", "No")
    del assessment_data["education"]

    response = create_real_prediction(token, assessment_data, monkeypatch)

    assert response.status_code == 409
    assert "education" in response.json()["detail"].lower()


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
            return PredictionCreate(
                assessment_id=assessment_id,
                risk_level="medium",
                risk_category="financial_access",
                probability=0.7,
                confidence=0.9,
                explanation="Injected test model output.",
                contributing_factors={"future_feature": 1},
                model_version="test-model",
            )

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

    listed = client.get(
        f"/api/v1/assessments/{assessment_id}/predictions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_prediction_endpoints_require_authentication():
    assert client.post("/api/v1/predictions", json={"assessment_id": 1}).status_code == 401
    assert client.get("/api/v1/predictions/1").status_code == 401
    assert client.get("/api/v1/assessments/1/predictions").status_code == 401

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.models import Assessment, Prediction, Recommendation, User
from backend.schemas import (
    AssessmentCreate,
    AssessmentResponse,
    PredictionCreate,
    PredictionResponse,
    RecommendationCreate,
    RecommendationResponse,
    UserCreate,
    UserResponse,
)


def test_valid_user_creation():
    user = UserCreate(
        full_name="  Amina Otieno ",
        email="amina@example.com",
        password="secure123",
    )

    assert user.full_name == "Amina Otieno"
    assert str(user.email) == "amina@example.com"
    assert user.password == "secure123"


def test_invalid_email_and_password_are_rejected():
    with pytest.raises(ValidationError):
        UserCreate(full_name="Amina Otieno", email="not-an-email", password="secure123")

    with pytest.raises(ValidationError):
        UserCreate(full_name="Amina Otieno", email="amina@example.com", password="short")

    with pytest.raises(ValidationError):
        UserCreate(full_name="Amina Otieno", email="amina@example.com", password="onlyletters")


def test_user_role_cannot_be_assigned_by_client():
    with pytest.raises(ValidationError):
        UserCreate(
            full_name="Amina Otieno",
            email="amina@example.com",
            password="secure123",
            role="admin",
        )


def test_user_response_is_safe_and_serializes_orm_object():
    user = User(
        id=1,
        full_name="Amina Otieno",
        email="amina@example.com",
        hashed_password="secret-hash",
        role="user",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    response = UserResponse.model_validate(user)
    payload = response.model_dump()

    assert payload["email"] == "amina@example.com"
    assert "password" not in payload
    assert "hashed_password" not in payload


def test_assessment_schema_accepts_flexible_data():
    assessment = AssessmentCreate(
        assessment_data={"future_feature": {"value": 10}},
        assessment_status=" DRAFT ",
    )

    assert assessment.assessment_data["future_feature"]["value"] == 10
    assert assessment.assessment_status == "draft"


def test_assessment_response_serializes_orm_object():
    now = datetime.now(timezone.utc)
    assessment = Assessment(
        id=2,
        user_id=1,
        assessment_status="completed",
        assessment_data={"score": 0.5},
        assessment_date=now,
        created_at=now,
        updated_at=now,
    )

    response = AssessmentResponse.model_validate(assessment)

    assert response.id == 2
    assert response.assessment_data == {"score": 0.5}


def test_prediction_schema_validates_ml_output():
    prediction = PredictionCreate(
        assessment_id=2,
        risk_level="medium",
        risk_category="access",
        probability=0.65,
        confidence=0.8,
        explanation="The model identified moderate risk.",
        contributing_factors={"factor_a": 0.4},
        model_version="1.0.0",
    )

    assert prediction.probability == 0.65

    with pytest.raises(ValidationError):
        PredictionCreate(
            assessment_id=2,
            risk_level="unknown",
            risk_category="access",
            probability=0.65,
            explanation="Explanation",
            model_version="1.0.0",
        )

    with pytest.raises(ValidationError):
        PredictionCreate(
            assessment_id=2,
            risk_level="low",
            risk_category="access",
            probability=1.1,
            explanation="Explanation",
            model_version="1.0.0",
        )


def test_prediction_response_serializes_orm_object():
    now = datetime.now(timezone.utc)
    prediction = Prediction(
        id=3,
        assessment_id=2,
        risk_level="low",
        risk_category="access",
        probability=0.2,
        confidence=None,
        explanation="Low predicted risk.",
        contributing_factors={"factor_a": 0.1},
        model_version="1.0.0",
        prediction_timestamp=now,
        created_at=now,
    )

    response = PredictionResponse.model_validate(prediction)

    assert response.id == 3
    assert response.probability == 0.2


def test_recommendation_schema_validates_priority_and_serializes_orm():
    recommendation = RecommendationCreate(
        prediction_id=3,
        category="financial_access",
        recommendation_text="Review available financial services.",
        priority=1,
    )
    assert recommendation.priority == 1

    with pytest.raises(ValidationError):
        RecommendationCreate(
            prediction_id=3,
            category="financial_access",
            recommendation_text="Review available financial services.",
            priority=6,
        )

    orm_recommendation = Recommendation(
        id=4,
        prediction_id=3,
        category="financial_access",
        recommendation_text="Review available financial services.",
        priority=1,
        created_at=datetime.now(timezone.utc),
    )
    response = RecommendationResponse.model_validate(orm_recommendation)

    assert response.id == 4
    assert response.priority == 1

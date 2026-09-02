"""
FINPATH Models Test Suite

Comprehensive tests for SQLAlchemy models including relationships, constraints, and database operations.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from datetime import datetime, timezone
from sqlalchemy import inspect, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from backend.models import User, Assessment, Prediction, Recommendation
from backend.database import Base


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def session(test_db):
    """Create a database session for testing."""
    SessionLocal = sessionmaker(bind=test_db)
    db = SessionLocal()
    yield db
    db.close()


class TestUserModel:
    """Test User model."""
    
    def test_user_creation(self, session):
        """Test basic user creation."""
        user = User(
            full_name="John Doe",
            email="john@example.com",
            hashed_password="hashed_password_123",
            role="user"
        )
        session.add(user)
        session.commit()
        
        assert user.id is not None
        assert user.email == "john@example.com"
        assert user.role == "user"
        assert user.is_active is True
        assert user.created_at is not None
    
    def test_user_email_uniqueness(self, session):
        """Test that email uniqueness constraint is enforced."""
        user1 = User(
            full_name="John Doe",
            email="john@example.com",
            hashed_password="hashed1",
            role="user"
        )
        user2 = User(
            full_name="Jane Doe",
            email="john@example.com",
            hashed_password="hashed2",
            role="user"
        )
        session.add(user1)
        session.commit()
        session.add(user2)
        
        with pytest.raises(IntegrityError):
            session.commit()
    
    def test_user_timestamps(self, session):
        """Test that timestamps are set correctly."""
        user = User(
            full_name="John Doe",
            email="john@example.com",
            hashed_password="hashed",
            role="user"
        )
        session.add(user)
        session.commit()
        
        assert user.created_at is not None
        assert user.updated_at is not None
        # Timestamps may differ by microseconds, so just check they're close
        time_diff = abs((user.updated_at - user.created_at).total_seconds())
        assert time_diff < 0.01  # Within 10 milliseconds


class TestAssessmentModel:
    """Test Assessment model."""
    
    def test_assessment_creation(self, session):
        """Test basic assessment creation."""
        user = User(
            full_name="John Doe",
            email="john@example.com",
            hashed_password="hashed",
            role="user"
        )
        session.add(user)
        session.commit()
        
        assessment = Assessment(
            user_id=user.id,
            assessment_status="submitted",
            assessment_data={"age": 25, "income": 50000}
        )
        session.add(assessment)
        session.commit()
        
        assert assessment.id is not None
        assert assessment.user_id == user.id
        assert assessment.assessment_status == "submitted"
        assert assessment.assessment_data == {"age": 25, "income": 50000}
    
    def test_assessment_default_status(self, session):
        """Test that assessment status defaults to 'draft'."""
        user = User(
            full_name="John Doe",
            email="john@example.com",
            hashed_password="hashed",
            role="user"
        )
        session.add(user)
        session.commit()
        
        assessment = Assessment(user_id=user.id)
        session.add(assessment)
        session.commit()
        
        assert assessment.assessment_status == "draft"
    
    def test_user_assessment_relationship(self, session):
        """Test User → Assessment relationship."""
        user = User(
            full_name="John Doe",
            email="john@example.com",
            hashed_password="hashed",
            role="user"
        )
        session.add(user)
        session.commit()
        
        assessment1 = Assessment(user_id=user.id)
        assessment2 = Assessment(user_id=user.id)
        session.add_all([assessment1, assessment2])
        session.commit()
        
        # Refresh to load relationships
        session.refresh(user)
        assert len(user.assessments) == 2
        assert assessment1 in user.assessments
        assert assessment2 in user.assessments


class TestPredictionModel:
    """Test Prediction model."""
    
    def test_prediction_creation(self, session):
        """Test basic prediction creation."""
        user = User(
            full_name="John Doe",
            email="john@example.com",
            hashed_password="hashed",
            role="user"
        )
        assessment = Assessment(user_id=1)
        session.add(user)
        session.add(assessment)
        session.commit()
        
        # Use the actual assessment ID
        prediction = Prediction(
            assessment_id=assessment.id,
            risk_level="medium",
            risk_category="moderate_inclusion_risk",
            probability=0.65,
            explanation="Based on assessment data",
            model_version="v1.0"
        )
        session.add(prediction)
        session.commit()
        
        assert prediction.id is not None
        assert prediction.assessment_id == assessment.id
        assert prediction.risk_level == "medium"
        assert prediction.probability == 0.65
    
    def test_assessment_prediction_relationship(self, session):
        """Test Assessment → Prediction relationship."""
        user = User(
            full_name="John Doe",
            email="john@example.com",
            hashed_password="hashed",
            role="user"
        )
        assessment = Assessment(user_id=1)
        session.add(user)
        session.add(assessment)
        session.commit()
        
        prediction1 = Prediction(
            assessment_id=assessment.id,
            risk_level="high",
            risk_category="high_risk",
            probability=0.85,
            explanation="Explanation 1",
            model_version="v1.0"
        )
        prediction2 = Prediction(
            assessment_id=assessment.id,
            risk_level="low",
            risk_category="low_risk",
            probability=0.15,
            explanation="Explanation 2",
            model_version="v1.0"
        )
        session.add_all([prediction1, prediction2])
        session.commit()
        
        session.refresh(assessment)
        assert len(assessment.predictions) == 2
        assert prediction1 in assessment.predictions
        assert prediction2 in assessment.predictions


class TestRecommendationModel:
    """Test Recommendation model."""
    
    def test_recommendation_creation(self, session):
        """Test basic recommendation creation."""
        user = User(
            full_name="John Doe",
            email="john@example.com",
            hashed_password="hashed",
            role="user"
        )
        assessment = Assessment(user_id=1)
        prediction = Prediction(
            assessment_id=1,
            risk_level="high",
            risk_category="high_risk",
            probability=0.85,
            explanation="High risk",
            model_version="v1.0"
        )
        session.add_all([user, assessment, prediction])
        session.commit()
        
        recommendation = Recommendation(
            prediction_id=prediction.id,
            category="financial_literacy",
            recommendation_text="Enroll in financial literacy program",
            priority=1
        )
        session.add(recommendation)
        session.commit()
        
        assert recommendation.id is not None
        assert recommendation.prediction_id == prediction.id
        assert recommendation.category == "financial_literacy"
        assert recommendation.priority == 1
    
    def test_recommendation_default_priority(self, session):
        """Test that recommendation priority defaults to 3."""
        user = User(
            full_name="John Doe",
            email="john@example.com",
            hashed_password="hashed",
            role="user"
        )
        assessment = Assessment(user_id=1)
        prediction = Prediction(
            assessment_id=1,
            risk_level="low",
            risk_category="low_risk",
            probability=0.15,
            explanation="Low risk",
            model_version="v1.0"
        )
        session.add_all([user, assessment, prediction])
        session.commit()
        
        recommendation = Recommendation(
            prediction_id=prediction.id,
            category="savings",
            recommendation_text="Start a savings account"
        )
        session.add(recommendation)
        session.commit()
        
        assert recommendation.priority == 3
    
    def test_prediction_recommendation_relationship(self, session):
        """Test Prediction → Recommendation relationship."""
        user = User(
            full_name="John Doe",
            email="john@example.com",
            hashed_password="hashed",
            role="user"
        )
        assessment = Assessment(user_id=1)
        prediction = Prediction(
            assessment_id=1,
            risk_level="medium",
            risk_category="medium_risk",
            probability=0.50,
            explanation="Medium risk",
            model_version="v1.0"
        )
        session.add_all([user, assessment, prediction])
        session.commit()
        
        rec1 = Recommendation(
            prediction_id=prediction.id,
            category="category1",
            recommendation_text="Recommendation 1"
        )
        rec2 = Recommendation(
            prediction_id=prediction.id,
            category="category2",
            recommendation_text="Recommendation 2"
        )
        session.add_all([rec1, rec2])
        session.commit()
        
        session.refresh(prediction)
        assert len(prediction.recommendations) == 2
        assert rec1 in prediction.recommendations
        assert rec2 in prediction.recommendations


class TestCompleteWorkflow:
    """Test the complete User → Assessment → Prediction → Recommendation workflow."""
    
    def test_full_workflow(self, session):
        """Test the complete financial inclusion assessment workflow."""
        # Create user
        user = User(
            full_name="Alice Kariuki",
            email="alice@example.com",
            hashed_password="hashed_secure_password",
            role="user",
            is_active=True
        )
        session.add(user)
        session.commit()
        
        # Create assessment
        assessment = Assessment(
            user_id=user.id,
            assessment_status="submitted",
            assessment_data={
                "age": 23,
                "employment_status": "informal",
                "monthly_income": 15000,
                "has_mobile_money": True
            }
        )
        session.add(assessment)
        session.commit()
        
        # Create prediction
        prediction = Prediction(
            assessment_id=assessment.id,
            risk_level="medium",
            risk_category="moderate_financial_inclusion_gap",
            probability=0.62,
            confidence=0.88,
            explanation="User shows moderate financial inclusion gap due to informal employment and limited banking access",
            contributing_factors={
                "employment_instability": 0.35,
                "limited_credit_history": 0.28,
                "digital_literacy": 0.25
            },
            model_version="finpath_v1.0"
        )
        session.add(prediction)
        session.commit()
        
        # Create recommendations
        recommendation1 = Recommendation(
            prediction_id=prediction.id,
            category="financial_literacy",
            recommendation_text="Enroll in beginner financial literacy program focusing on savings and budgeting",
            priority=1
        )
        recommendation2 = Recommendation(
            prediction_id=prediction.id,
            category="digital_banking",
            recommendation_text="Open a digital bank account with low/no minimum balance requirements",
            priority=2
        )
        recommendation3 = Recommendation(
            prediction_id=prediction.id,
            category="micro_credit",
            recommendation_text="Consider joining a savings group for access to micro-credit",
            priority=3
        )
        session.add_all([recommendation1, recommendation2, recommendation3])
        session.commit()
        
        # Verify entire workflow
        session.refresh(user)
        assert len(user.assessments) == 1
        
        session.refresh(assessment)
        assert len(assessment.predictions) == 1
        
        session.refresh(prediction)
        assert len(prediction.recommendations) == 3
        
        # Verify data integrity
        assert user.email == "alice@example.com"
        assert assessment.assessment_data["age"] == 23
        assert prediction.probability == 0.62
        assert recommendation1.priority == 1


def test_model_imports():
    """Test that all models can be imported successfully."""
    from backend.models import User, Assessment, Prediction, Recommendation
    
    assert User is not None
    assert Assessment is not None
    assert Prediction is not None
    assert Recommendation is not None


def test_sqlalchemy_metadata():
    """Test that SQLAlchemy metadata recognizes all models."""
    from backend.database import Base
    from backend.models import User, Assessment, Prediction, Recommendation
    
    table_names = {table.name for table in Base.metadata.tables.values()}
    
    assert "users" in table_names
    assert "assessments" in table_names
    assert "predictions" in table_names
    assert "recommendations" in table_names


def test_table_creation(test_db):
    """Test that all tables can be created successfully."""
    from backend.database import Base
    from backend.models import User, Assessment, Prediction, Recommendation
    
    inspector = inspect(test_db)
    table_names = inspector.get_table_names()
    
    assert "users" in table_names
    assert "assessments" in table_names
    assert "predictions" in table_names
    assert "recommendations" in table_names


def test_foreign_key_constraints(test_db):
    """Test that foreign key constraints are properly defined."""
    inspector = inspect(test_db)
    
    # Check assessment → user foreign key
    assessment_fks = inspector.get_foreign_keys("assessments")
    assert any(fk["constrained_columns"] == ["user_id"] for fk in assessment_fks)
    
    # Check prediction → assessment foreign key
    prediction_fks = inspector.get_foreign_keys("predictions")
    assert any(fk["constrained_columns"] == ["assessment_id"] for fk in prediction_fks)
    
    # Check recommendation → prediction foreign key
    recommendation_fks = inspector.get_foreign_keys("recommendations")
    assert any(fk["constrained_columns"] == ["prediction_id"] for fk in recommendation_fks)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

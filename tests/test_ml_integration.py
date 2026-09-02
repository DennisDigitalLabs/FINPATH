from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.schemas.prediction import PredictionCreate
from backend.services.prediction_service import (
    AssessmentDataInputAdapter,
    ModelArtifactLoader,
    PredictionOutputAdapter,
    PredictionService,
    PredictionUnavailableError,
    UnavailableMLPredictor,
)


def valid_output(assessment_id: int = 7) -> dict:
    return {
        "assessment_id": assessment_id,
        "risk_level": "medium",
        "risk_category": "Moderate Risk",
        "probability": 0.72,
        "confidence": 0.88,
        "explanation": "Validated model explanation.",
        "contributing_factors": {"approved_factor": 0.4},
        "model_version": "approved-version",
    }


def test_predictor_contract_and_input_adapter_preserve_structured_data():
    assessment_data = {"future_feature": {"value": 3}}
    with pytest.raises(ValueError, match="Age"):
        AssessmentDataInputAdapter().prepare(assessment_data)

    with pytest.raises(PredictionUnavailableError):
        UnavailableMLPredictor().predict({"Age": 25})


def test_output_adapter_accepts_valid_mapping_and_preserves_contract():
    result = PredictionOutputAdapter().validate(valid_output(), assessment_id=7)
    assert isinstance(result, PredictionCreate)
    assert result.model_version == "approved-version"
    assert result.contributing_factors == {"approved_factor": 0.4}


def test_output_adapter_rejects_invalid_output_without_fabrication():
    for field, value in (("risk_level", "unknown"), ("probability", 1.2), ("confidence", -0.1)):
        output = valid_output()
        output[field] = value
        with pytest.raises(ValidationError):
            PredictionOutputAdapter().validate(output, assessment_id=7)


def test_real_predictor_rejects_unknown_risk_categories():
    with pytest.raises(ValueError, match="Unsupported ML risk category"):
        PredictionOutputAdapter().validate(
            {**valid_output(), "risk_level": None, "risk_category": "Unexpected Risk"},
            assessment_id=7,
        )

    missing_explanation = valid_output()
    del missing_explanation["explanation"]
    result = PredictionOutputAdapter().validate(missing_explanation, assessment_id=7)
    assert result.explanation
    assert "FINPATH model predicted" in result.explanation


def test_output_adapter_rejects_mismatched_validated_result():
    result = PredictionCreate.model_validate(valid_output(assessment_id=99))
    with pytest.raises(ValueError, match="does not match"):
        PredictionOutputAdapter().validate(result, assessment_id=7)


def test_model_artifact_loader_requires_configured_existing_local_file(tmp_path: Path):
    with pytest.raises(PredictionUnavailableError):
        ModelArtifactLoader(None).validate_path()

    missing = ModelArtifactLoader(str(tmp_path / "missing-artifact"))
    with pytest.raises(PredictionUnavailableError):
        missing.validate_path()

    artifact = tmp_path / "approved-artifact"
    artifact.write_text("test placeholder", encoding="ascii")
    assert ModelArtifactLoader(str(artifact)).validate_path() == artifact


def test_prediction_service_defaults_to_fail_closed_predictor():
    service = PredictionService()
    assert isinstance(service.predictor, UnavailableMLPredictor)
    with pytest.raises(PredictionUnavailableError):
        service.predictor.predict({"data": "test"})


def test_assessment_input_adapter_maps_required_finpath_fields_and_rejects_missing_values():
    source = {
        "age": 25,
        "gender": 2,
        "county_code": 47,
        "education": 5,
        "marital_status": 1,
        "has_chama": 0,
        "Savings_usage": 1,
        "Loan_usage": 0,
        "Loan_formal": 0,
        "Loan_informal": 1,
        "Digital_credit_usage": 0,
        "defaulted": 0,
        "loan_app_2": 0,
        "loan_fuliza_2": 0,
        "chama_usage": 0,
        "sacco_use": 3,
        "mobile_money_use": 1,
        "experienced_shock": 0,
        "Financial_literacy_index_fnl": 3,
        "accessto_13k_1month": 0,
        "S7_2": 4,
        "saving_for_emergencies": 0,
        "CountLivelihood": 1,
    }

    prepared = AssessmentDataInputAdapter().prepare(source)

    assert prepared["Age"] == 2
    assert prepared["Sex"] == 2
    assert prepared["county"] == 47
    assert prepared["A20"] == 5
    assert prepared["A21"] == 1
    assert prepared["Savings_usage"] == 1
    assert prepared["CountLivelihood"] == 1

    missing = {k: v for k, v in source.items() if k not in {"Age", "age"}}
    with pytest.raises(ValueError, match="Age"):
        AssessmentDataInputAdapter().prepare(missing)

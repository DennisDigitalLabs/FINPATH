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
    assert "The model predicted" in result.explanation


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
        "age_range": "25-34",
        "sex": 2,
        "county": 47,
        "education": 5,
        "marital_status": 1,
        "savings_usage": 1,
        "emergency_savings": 0,
        "loan_usage": 0,
        "loan_formal": 0,
        "loan_informal": 1,
        "digital_credit_usage": 0,
        "defaulted": 0,
        "loan_app_2": 0,
        "loan_fuliza_2": 0,
        "chama_usage": 0,
        "sacco_use": 3,
        "mobile_money_use": 1,
        "S7_2": 4,
        "CountLivelihood": 1,
        "financial_literacy_score": 3,
    }

    prepared = AssessmentDataInputAdapter().prepare(source)

    assert prepared["Age"] == 3
    assert prepared["Sex"] == 2
    assert prepared["county"] == 47
    assert prepared["A20"] == 5
    assert prepared["A21"] == 1
    assert prepared["Savings_usage"] == 1
    assert prepared["CountLivelihood"] == 1
    assert prepared["Financial_literacy_index_fnl"] == 3

    missing = {k: v for k, v in source.items() if k != "age_range"}

    with pytest.raises(ValueError, match="Age range"):
        AssessmentDataInputAdapter().prepare(missing)


def browser_assessment_data(**overrides):
    data = {
        "age_range": "18-24",
        "sex": "Female",
        "county": "Nairobi City",
        "education": "Secondary completed",
        "marital_status": "Single / Never Married",
        "savings_usage": "Yes",
        "emergency_savings": "Yes",
        "loan_usage": "No",
        "chama_usage": "No",
        "sacco_use": "No",
        "mobile_money_use": "No",
        "CountLivelihood": "1",
        "financial_literacy_score": "3",
    }
    data.update(overrides)
    return data


def test_browser_assessment_values_map_to_trained_contract():
    adapter = AssessmentDataInputAdapter()

    no_loan = adapter.prepare(browser_assessment_data())
    assert no_loan["saving_for_emergencies"] == 1
    assert no_loan["Loan_usage"] == 0
    assert no_loan["Loan_formal"] == 0
    assert no_loan["Loan_informal"] == 0
    assert no_loan["Digital_credit_usage"] == 0
    assert no_loan["loan_app_2"] == 0
    assert no_loan["loan_fuliza_2"] == 0
    assert no_loan["defaulted"] == 0
    assert no_loan["sacco_use"] == 3
    assert no_loan["mobile_money_use"] == 3
    assert no_loan["S7_2"] == 4

    loan_user = adapter.prepare(browser_assessment_data(
        emergency_savings="No",
        loan_usage="Yes",
        loan_formal="Yes",
        loan_informal="No",
        digital_credit_usage="Yes",
        loan_app_2="No",
        loan_fuliza_2="No",
        defaulted="No",
        sacco_use="Regular",
        mobile_money_use="Occasional",
        S7_2="A few times a month",
    ))
    assert loan_user["saving_for_emergencies"] == 0
    assert loan_user["Loan_usage"] == 1
    assert loan_user["Loan_formal"] == 1
    assert loan_user["Loan_informal"] == 0
    assert loan_user["Digital_credit_usage"] == 1
    assert loan_user["loan_app_2"] == 0
    assert loan_user["loan_fuliza_2"] == 0
    assert loan_user["defaulted"] == 0
    assert loan_user["sacco_use"] == 1
    assert loan_user["mobile_money_use"] == 1
    assert loan_user["S7_2"] == 3

    assert adapter.prepare(browser_assessment_data(sacco_use="Occasional"))["sacco_use"] == 1
    assert adapter.prepare(browser_assessment_data(mobile_money_use="Regular", S7_2="Several times a week"))["mobile_money_use"] == 1

    for value in ("35-44", 1, 4, 5, 6):
        with pytest.raises(ValueError, match="age"):
            adapter.prepare(browser_assessment_data(age_range=value))


def test_browser_emergency_savings_values_are_binary():
    adapter = AssessmentDataInputAdapter()
    assert adapter.prepare(browser_assessment_data(emergency_savings="Yes"))["saving_for_emergencies"] == 1
    assert adapter.prepare(browser_assessment_data(emergency_savings="No"))["saving_for_emergencies"] == 0

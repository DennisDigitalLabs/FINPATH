import logging
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
from ml.predict import (
    ARTIFACT_FILES,
    FinpathPredictor,
    ModelArtifactIntegrityError,
    verify_model_artifacts,
    write_model_artifact_manifest,
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


def test_model_artifact_manifest_detects_tampering(tmp_path: Path):
    for filename in ARTIFACT_FILES:
        contents = f"synthetic-{filename}".encode("ascii")
        (tmp_path / filename).write_bytes(contents)

    write_model_artifact_manifest(tmp_path)
    verify_model_artifacts(tmp_path)
    (tmp_path / "label_encoder.joblib").write_bytes(b"modified")
    with pytest.raises(ModelArtifactIntegrityError):
        verify_model_artifacts(tmp_path)


def test_model_input_allowlist_drops_context_and_rejects_unknown_fields():
    normalized = FinpathPredictor._normalize({
        "Age": 25,
        "monthly_income": "25000",
    })

    assert normalized["Age"] == 2
    assert "monthly_income" not in normalized
    with pytest.raises(ValueError, match="unsupported fields"):
        FinpathPredictor._normalize({"Age": 25, "unapproved_field": "value"})
    with pytest.raises(ValueError, match="Age"):
        FinpathPredictor._normalize({"Age": 25.5})
    with pytest.raises(ValueError, match="invalid values"):
        FinpathPredictor._normalize({"Age": 25, "Sex": {"value": 2}})


def test_explainability_failure_does_not_log_exception_text(monkeypatch, caplog, capsys):
    import numpy as np

    class TestModel:
        def predict_proba(self, _features):
            return np.array([[0.2, 0.3, 0.5]])

    class TestLabelEncoder:
        classes_ = ["High Risk", "Low Risk", "Moderate Risk"]

    monkeypatch.setattr(
        "ml.predict.joblib.load",
        lambda path: TestModel() if Path(path).name == "finpath_model.joblib" else TestLabelEncoder(),
    )

    def fail_with_sensitive_detail(*_args, **_kwargs):
        raise RuntimeError("SENSITIVE_TEST_DETAIL")

    monkeypatch.setattr("ml.explain_model.explain", fail_with_sensitive_detail)
    with caplog.at_level(logging.WARNING, logger="ml.predict"):
        predictor = FinpathPredictor()
        result = predictor.predict({"Age": 25})

    assert result["risk_category"] == "Moderate Risk"
    assert "SENSITIVE_TEST_DETAIL" not in caplog.text
    assert capsys.readouterr().out == ""


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


def test_mapper_uses_existing_model_defaults_only_for_not_applicable_fields():
    source = {
        "age_range": "25-34",
        "sex": 2,
        "county": 47,
        "education": 5,
        "marital_status": 1,
        "savings_usage": 1,
        "emergency_savings": 0,
        "loan_usage": "No",
        "chama_usage": 0,
        "sacco_use": 3,
        "mobile_money_use": "No",
        "CountLivelihood": 1,
        "financial_literacy_score": 3,
    }

    prepared = AssessmentDataInputAdapter().prepare(source)

    assert {field: prepared[field] for field in (
        "Loan_formal", "Loan_informal", "Digital_credit_usage",
        "loan_app_2", "loan_fuliza_2", "defaulted", "S7_2",
    )} == {
        "Loan_formal": 0,
        "Loan_informal": 0,
        "Digital_credit_usage": 0,
        "loan_app_2": 0,
        "loan_fuliza_2": 0,
        "defaulted": 0,
        "S7_2": 4,
    }

    source["loan_usage"] = "Yes"
    source.update({
        "loan_informal": "No",
        "digital_credit_usage": "No",
        "loan_app_2": "No",
        "loan_fuliza_2": "No",
        "defaulted": "No",
    })
    with pytest.raises(ValueError, match="Formal loan is required"):
        AssessmentDataInputAdapter().prepare(source)

    source["loan_formal"] = "No"
    source["mobile_money_use"] = "Regular"
    with pytest.raises(ValueError, match="transaction frequency is required"):
        AssessmentDataInputAdapter().prepare(source)

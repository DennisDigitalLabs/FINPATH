# FINPATH ML Integration Contract

This document defines the backend boundary for connecting Yvette's approved FINPATH model. It does not select an algorithm, target variable, feature list, serialization format, or explainability method.

## Input

The prediction API accepts an owned assessment ID:

`POST /api/v1/predictions`

The backend retrieves the completed assessment and passes its validated `assessment_data` mapping to `MLInputAdapter.prepare()`. `AssessmentDataInputAdapter` currently preserves the mapping without inventing feature names. Replace or inject this adapter with the finalized feature mapping when the approved ML contract is available.

## Predictor interface

Implement `MLPredictor.predict(model_input)` and inject it into `PredictionService`. The predictor may use any approved model algorithm. It must return output accepted by `PredictionOutputAdapter`, either as a mapping or `PredictionCreate` instance.

Required output fields:

- `risk_level`: `low`, `medium`, or `high`
- `risk_category`: non-empty category text
- `probability`: number from `0` to `1`
- `confidence`: optional number from `0` to `1`
- `explanation`: non-empty human-readable explanation
- `contributing_factors`: optional structured mapping
- `model_version`: non-empty version identifier
- `prediction_timestamp`: optional timestamp

The output adapter validates these fields and associates the result with the requested assessment. Missing required values and invalid ranges are rejected; no values are fabricated.

## Artifacts and versioning

`MODEL_PATH` and `MODEL_VERSION` are environment-driven settings. `ModelArtifactLoader` validates that a configured artifact is a local regular file, but deliberately does not deserialize it because the approved format and trusted loading strategy have not been established. Do not accept a model path from an API request or a remote URL.

The configured model should report or be paired with an established version. Do not use a final production version until Yvette provides it.

## Explainability

The model layer owns the explainability methodology. The backend accepts the overall `explanation` and optional structured `contributing_factors` without calculating SHAP, LIME, feature importance, or other explanations.

## Unavailable model behavior

The default production predictor is `UnavailableMLPredictor`. Until a real predictor is injected and configured, `POST /api/v1/predictions` returns HTTP `503`. Tests may inject a test predictor, but production never silently falls back to test or fabricated output.

## Connection example

```python
class ApprovedFinpathPredictor:
    def predict(self, model_input):
        return {
            "risk_level": approved_level,
            "risk_category": approved_category,
            "probability": approved_probability,
            "confidence": approved_confidence,
            "explanation": approved_explanation,
            "contributing_factors": approved_factors,
            "model_version": approved_version,
        }

service = PredictionService(
    predictor=ApprovedFinpathPredictor(),
    input_adapter=ApprovedFinpathInputAdapter(),
)
```

The example values are placeholders for the approved model output and are not predictions.
from pathlib import Path
import hashlib
import hmac
import json
import logging
import math
import joblib
from typing import Any, Mapping
import numpy as np
import pandas as pd
from .feature_engineering import engineer_features
from .recommendation import recommendations
ROOT = Path(__file__).resolve().parents[1]
logger = logging.getLogger(__name__)

ARTIFACT_MANIFEST = "artifact_manifest.json"
ARTIFACT_FILES = (
    "finpath_model.joblib",
    "label_encoder.joblib",
    "scaler.joblib",
    "encoder.joblib",
    "metadata.json",
    "feature_names.json",
)

DEFAULTS = {
    'Sex': 1, 'county': 47, 'A20': 5, 'A21': 1, 'Savings_usage': 0, 'Loan_usage': 0,
    'Loan_formal': 0, 'Loan_informal': 0, 'Digital_credit_usage': 0, 'defaulted': 0,
    'loan_app_2': 0, 'loan_fuliza_2': 0, 'chama_usage': 0, 'sacco_use': 3,
    'mobile_money_use': 1, 'experienced_shock': 0, 'Financial_literacy_index_fnl': 3,
    'accessto_13k_1month': 0, 'S7_2': 4, 'saving_for_emergencies': 0, 'CountLivelihood': 1
}

MODEL_INPUT_FIELDS = frozenset(DEFAULTS) | {"Age"}
MODEL_CONTEXT_FIELDS = frozenset({
    "employment_status", "monthly_income", "income_reliability",
    "monthly_expenses", "financial_dependents", "bill_pressure",
    "saves_regularly", "budgeting", "location_type", "household_size",
    "debt_repayment", "credit_barrier", "account_access", "service_distance",
    "digital_confidence", "accessto_13k_1month", "financial_confidence",
    "financial_information", "future_goal",
})
MODEL_INPUT_ALIASES = frozenset({
    "age", "gender", "county_code", "education", "marital_status",
    "has_chama", "mobile_loan_usage",
})
ALLOWED_MODEL_INPUT_FIELDS = (
    MODEL_INPUT_FIELDS | MODEL_CONTEXT_FIELDS | MODEL_INPUT_ALIASES
)


class ModelArtifactIntegrityError(RuntimeError):
    """Raised when a configured model artifact does not match its manifest."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_model_artifact_manifest(model_dir: Path) -> None:
    root = model_dir.resolve(strict=True)
    manifest = {}
    for filename in ARTIFACT_FILES:
        artifact_path = root / filename
        if artifact_path.is_symlink() or not artifact_path.is_file():
            raise ModelArtifactIntegrityError(
                "A required FINPATH model artifact is unavailable"
            )
        manifest[filename] = _sha256_file(artifact_path)
    (root / ARTIFACT_MANIFEST).write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )


def verify_model_artifacts(
    model_dir: Path,
    filenames: tuple[str, ...] = ARTIFACT_FILES,
) -> None:
    if not filenames or any(filename not in ARTIFACT_FILES for filename in filenames):
        raise ModelArtifactIntegrityError(
            "The FINPATH model artifact manifest request is invalid"
        )
    try:
        root = model_dir.resolve(strict=True)
        manifest_path = root / ARTIFACT_MANIFEST
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise ModelArtifactIntegrityError
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, RuntimeError) as exc:
        raise ModelArtifactIntegrityError(
            "The FINPATH model artifact manifest is unavailable or invalid"
        ) from exc
    if not isinstance(manifest, dict) or set(manifest) != set(ARTIFACT_FILES):
        raise ModelArtifactIntegrityError(
            "The FINPATH model artifact manifest is incomplete"
        )

    for filename in filenames:
        artifact_path = root / filename
        expected_digest = manifest[filename]
        if (
            not isinstance(expected_digest, str)
            or len(expected_digest) != 64
            or any(character not in "0123456789abcdef" for character in expected_digest)
            or artifact_path.is_symlink()
            or not artifact_path.is_file()
        ):
            raise ModelArtifactIntegrityError(
                "A FINPATH model artifact failed integrity verification"
            )
        try:
            actual_digest = _sha256_file(artifact_path)
        except OSError as exc:
            raise ModelArtifactIntegrityError(
                "A FINPATH model artifact is unavailable"
            ) from exc
        if not hmac.compare_digest(actual_digest, expected_digest):
            raise ModelArtifactIntegrityError(
                "A FINPATH model artifact failed integrity verification"
            )


class FinpathPredictor:
    def __init__(self, model_dir=None):
        self.model_dir = Path(model_dir or ROOT / 'models' / 'v1')
        verify_model_artifacts(self.model_dir)
        self.model = joblib.load(self.model_dir / 'finpath_model.joblib')
        self.label_encoder = joblib.load(self.model_dir / 'label_encoder.joblib')
        self.metadata = json.loads((self.model_dir / 'metadata.json').read_text())

    @staticmethod
    def _normalize(payload: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise ValueError("Model input must be a mapping")
        p = dict(payload)
        if any(not isinstance(key, str) for key in p):
            raise ValueError("Model input contains unsupported fields")
        if set(p) - ALLOWED_MODEL_INPUT_FIELDS:
            raise ValueError("Model input contains unsupported fields")
        if any(
            not isinstance(value, (str, int, float, bool, type(None)))
            or isinstance(value, float) and not math.isfinite(value)
            or isinstance(value, str) and len(value) > 500
            for value in p.values()
        ):
            raise ValueError("Model input contains invalid values")
        age = p.get('Age', p.get('age'))
        if age is None:
            raise ValueError('Age is required.')
        if isinstance(age, bool):
            raise ValueError("Age must be a supported range code or age")
        if isinstance(age, str):
            age = age.strip()
            if not age.isdigit():
                raise ValueError("Age must be a supported range code or age")
        elif isinstance(age, float) and not age.is_integer():
            raise ValueError("Age must be a supported range code or age")
        try:
            age = int(age)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Age must be a supported range code or age") from exc
        if age in (1,2,3,4,5,6):
            age_code = age
        elif 18 <= age <= 25:
            age_code = 2
        elif 26 <= age <= 35:
            age_code = 3
        else:
            raise ValueError('Age must be between 18 and 35 for the FINPATH youth model.')
        p['Age'] = age_code
        aliases = {'gender':'Sex','county_code':'county','education':'A20','marital_status':'A21',
                   'has_chama':'chama_usage','mobile_loan_usage':'Digital_credit_usage'}
        for src,dst in aliases.items():
            if src in p and dst not in p: p[dst] = p[src]
        for k,v in DEFAULTS.items(): p.setdefault(k,v)
        return {key: value for key, value in p.items() if key in MODEL_INPUT_FIELDS}

    def predict(self, payload):
        p = self._normalize(payload)
        x = engineer_features(pd.DataFrame([p]))
        probs_arr = self.model.predict_proba(x)[0]
        classes = [str(c) for c in self.label_encoder.classes_]
        probs = {c: float(v) for c,v in zip(classes, probs_arr)}
        pred_class = classes[int(np.argmax(probs_arr))]
        risk_score = float(probs.get('High Risk',0.0) + 0.5*probs.get('Moderate Risk',0.0))
        factors = []
        try:
            from .explain_model import explain
            factors = explain(p, model_dir=self.model_dir)
        except Exception as exc:
            # Explainability is optional; prediction must still succeed if it fails.
            logger.warning("Explainability unavailable; prediction completed without explanation")
        return {'risk_score':risk_score,'risk_category':pred_class,'class_probabilities':probs,
                'top_contributing_factors':factors[:3],'recommendations':recommendations(p,factors),
                'model_version':self.metadata.get('model_version','v1')}

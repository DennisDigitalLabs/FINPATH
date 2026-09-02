from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol

from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models import Assessment, Prediction, Recommendation, User
from backend.schemas.prediction import PredictionCreate
from backend.services.ml_input_mapper import MLInputMapper, MLInputValidationError
from ml.predict import FinpathPredictor


class PredictionUnavailableError(RuntimeError):
	"""Raised when the trained FINPATH model is missing or unavailable."""


class MLInputAdapter(Protocol):
	def prepare(self, assessment_data: Mapping[str, Any]) -> Any:
		"""Convert validated assessment data to the model's input contract."""


class AssessmentDataInputAdapter:
	"""Translate assessment payloads into the exact FINPATH ML feature contract."""

	@staticmethod
	def _coerce_int(value: Any, field_name: str) -> int:
		if value is None or value == "":
			raise ValueError(f"Assessment data is missing required field '{field_name}'")
		try:
			return int(value)
		except (TypeError, ValueError) as exc:
			raise ValueError(f"Assessment field '{field_name}' must be an integer") from exc

	@staticmethod
	def _coerce_age(value: Any) -> int:
		if value is None or value == "":
			raise ValueError("Assessment data is missing required field 'Age'")
		if isinstance(value, str):
			text = value.strip().lower()
			if text in {"18-24", "18 to 24", "18-25"}:
				return 2
			if text in {"25-34", "26-35", "25 to 34"}:
				return 3
			if text.isdigit():
				value = int(text)
			else:
				raise ValueError("Age must be between 18 and 35 for the FINPATH youth model")
		age = int(value)
		if age in (1, 2, 3, 4, 5, 6):
			return age
		if 18 <= age <= 25:
			return 2
		if 26 <= age <= 35:
			return 3
		raise ValueError("Age must be between 18 and 35 for the FINPATH youth model")

	def _normalize_mapping(self, payload: Mapping[str, Any]) -> dict[str, Any]:
		result: dict[str, Any] = {}
		for key in payload:
			if isinstance(key, str):
				result[key] = payload[key]
		if "Age" not in result and "age" in result:
			result["Age"] = result.pop("age")
		if "Age" not in result and "age_range" in result:
			result["Age"] = result.pop("age_range")
		if "Sex" not in result and "gender" in result:
			result["Sex"] = result.pop("gender")
		if "county" not in result and "county_code" in result:
			result["county"] = result.pop("county_code")
		if "A20" not in result and "education" in result:
			result["A20"] = result.pop("education")
		if "A21" not in result and "marital_status" in result:
			result["A21"] = result.pop("marital_status")
		if "Digital_credit_usage" not in result and "mobile_loan_usage" in result:
			result["Digital_credit_usage"] = result.pop("mobile_loan_usage")
		if "chama_usage" not in result and "has_chama" in result:
			result["chama_usage"] = result.pop("has_chama")
		if "loan_app_2" not in result and "loan_app_usage" in result:
			result["loan_app_2"] = result.pop("loan_app_usage")
		if "loan_fuliza_2" not in result and "fuliza_usage" in result:
			result["loan_fuliza_2"] = result.pop("fuliza_usage")
		if "saving_for_emergencies" not in result and "emergency_savings" in result:
			result["saving_for_emergencies"] = result.pop("emergency_savings")
		return result

	def prepare(self, assessment_data: Mapping[str, Any]) -> Mapping[str, Any]:
		if not isinstance(assessment_data, Mapping):
			raise ValueError("Assessment data must be a mapping")
		payload = dict(assessment_data)
		recognized_keys = {
			"Age", "age", "age_range", "Sex", "gender", "county", "county_code",
			"A20", "education", "A21", "marital_status", "Digital_credit_usage",
			"mobile_loan_usage", "chama_usage", "has_chama", "loan_app_2", "loan_app_usage",
			"loan_fuliza_2", "fuliza_usage", "saving_for_emergencies", "emergency_savings",
		}
		if not any(key in payload for key in recognized_keys):
			raise ValueError("Assessment data is missing required field 'Age'")
		payload = self._normalize_mapping(payload)
		if "Age" in payload:
			payload["Age"] = self._coerce_age(payload["Age"])
		elif "age" in payload:
			payload["Age"] = self._coerce_age(payload["age"])
		else:
			raise ValueError("Assessment data is missing required field 'Age'")
		if "Sex" not in payload and "gender" in payload:
			payload["Sex"] = self._coerce_int(payload["gender"], "Sex")
		if "county" not in payload and "county_code" in payload:
			payload["county"] = self._coerce_int(payload["county_code"], "county")
		if "A20" not in payload and "education" in payload:
			payload["A20"] = self._coerce_int(payload["education"], "A20")
		if "A21" not in payload and "marital_status" in payload:
			payload["A21"] = self._coerce_int(payload["marital_status"], "A21")
		if "Sex" in payload:
			sex_value = payload["Sex"]
			if isinstance(sex_value, str):
				lookup = {"male": 1, "female": 2, "m": 1, "f": 2}
				payload["Sex"] = lookup.get(sex_value.strip().lower(), sex_value)
			if isinstance(payload["Sex"], str):
				raise ValueError("Sex must be 1 for Male or 2 for Female")
		if "county" in payload and isinstance(payload["county"], str) and payload["county"].strip().isdigit():
			payload["county"] = int(payload["county"])
		return payload


class MLPredictor(Protocol):
	def predict(self, model_input: Any) -> Any:
		"""Return raw output from the trained FINPATH model."""


class MLOutputAdapter(Protocol):
	def validate(self, model_output: Any, assessment_id: int) -> PredictionCreate:
		"""Convert model output into the backend prediction contract."""


class PredictionOutputAdapter:
	@staticmethod
	def _risk_level_for(category: str) -> str:
		mapping = {
			"high risk": "high",
			"moderate risk": "medium",
			"low risk": "low",
		}
		key = str(category).strip().lower()
		if key not in mapping:
			raise ValueError(f"Unsupported ML risk category: {category}")
		return mapping[key]

	@staticmethod
	def _probability_from_output(model_output: Mapping[str, Any]) -> float:
		if "probability" in model_output and model_output["probability"] is not None:
			return float(model_output["probability"])
		class_probabilities = model_output.get("class_probabilities")
		if isinstance(class_probabilities, Mapping):
			values = [float(v) for v in class_probabilities.values() if isinstance(v, (int, float))]
			if values:
				return max(values)
		if "risk_score" in model_output:
			return float(model_output["risk_score"])
		raise ValueError("ML model output is missing a valid probability value")

	@staticmethod
	def _build_explanation(model_output: Mapping[str, Any]) -> str:
		if model_output.get("explanation"):
			return str(model_output["explanation"]).strip()
		category = str(model_output.get("risk_category") or "predicted risk")
		probability = PredictionOutputAdapter._probability_from_output(model_output)
		return f"FINPATH model predicted {category} with a top-class probability of {probability:.2%}."

	@staticmethod
	def _build_contributing_factors(model_output: Mapping[str, Any]) -> dict[str, Any] | None:
		if "contributing_factors" in model_output and model_output["contributing_factors"] is not None:
			return dict(model_output["contributing_factors"])
		factors = model_output.get("top_contributing_factors")
		if isinstance(factors, list) and factors:
			return {"top_factors": [dict(item) if isinstance(item, Mapping) else {"feature": str(item)} for item in factors]}
		return None

	def validate(self, model_output: Any, assessment_id: int) -> PredictionCreate:
		if isinstance(model_output, PredictionCreate):
			if model_output.assessment_id != assessment_id:
				raise ValueError("Prediction output does not match the assessment")
			values = model_output.model_dump()
		else:
			if not isinstance(model_output, Mapping):
				raise ValueError("ML predictor returned an unsupported output")
			values = dict(model_output)
			if "assessment_id" in values and values["assessment_id"] != assessment_id:
				raise ValueError("Prediction output does not match the assessment")
		if "risk_category" not in values:
			raise ValueError("ML model output is missing 'risk_category'")
		if "risk_level" not in values or values["risk_level"] is None:
			values["risk_level"] = self._risk_level_for(str(values["risk_category"]))
		values["probability"] = self._probability_from_output(values)
		values["confidence"] = values.get("confidence")
		values["explanation"] = self._build_explanation(values)
		if values.get("contributing_factors") is None:
			values["contributing_factors"] = self._build_contributing_factors(values)
		values["model_version"] = str(values.get("model_version") or "v1")
		values["assessment_id"] = assessment_id
		if "prediction_timestamp" in values and values["prediction_timestamp"] is None:
			del values["prediction_timestamp"]
		prediction_fields = {
			"assessment_id",
			"risk_level",
			"risk_category",
			"probability",
			"confidence",
			"explanation",
			"contributing_factors",
			"model_version",
			"prediction_timestamp",
		}
		return PredictionCreate.model_validate(
			{key: value for key, value in values.items() if key in prediction_fields}
		)


class UnavailableMLPredictor:
	def predict(self, model_input: Any) -> Any:
		raise PredictionUnavailableError("The FINPATH prediction model is not available")


class ModelArtifactLoader:
	"""Validate a trusted local model artifact path without accepting remote inputs."""

	def __init__(self, model_path: str | None):
		self.model_path = Path(model_path).expanduser() if model_path else None

	def validate_path(self) -> Path:
		if self.model_path is None:
			raise PredictionUnavailableError("The FINPATH prediction model is not configured")
		if self.model_path.is_dir():
			candidate = self.model_path / "finpath_model.joblib"
			if candidate.is_file():
				return candidate
			raise PredictionUnavailableError("The FINPATH prediction artifact is unavailable")
		if not self.model_path.is_file():
			raise PredictionUnavailableError("The FINPATH prediction artifact is unavailable")
		return self.model_path


class RealFinpathPredictor:
	def __init__(self, model_path: str | None = None, model_version: str | None = None):
		settings = get_settings()
		self.model_version = model_version or settings.MODEL_VERSION or "v1"
		configured = model_path or settings.MODEL_PATH or str(settings.model_directory)
		self.loader = ModelArtifactLoader(configured)
		artifact = self.loader.validate_path()
		self.model_dir = artifact.parent
		self.model = FinpathPredictor(model_dir=str(self.model_dir))

	def predict(self, model_input: Any) -> Any:
		try:
			result = self.model.predict(model_input)
		except Exception as exc:  # pragma: no cover - fail closed at the service boundary
			raise PredictionUnavailableError("The FINPATH prediction model could not process the input") from exc
		if isinstance(result, Mapping):
			result = dict(result)
			result.setdefault("model_version", self.model_version)
			if "risk_category" in result and "risk_level" not in result:
				result["risk_level"] = ResultMappingAdapter.normalize_risk_level(result["risk_category"])
		return result


class ResultMappingAdapter:
	@staticmethod
	def normalize_risk_level(category: Any) -> str:
		mapping = {
			"high risk": "high",
			"moderate risk": "medium",
			"low risk": "low",
		}
		key = str(category).strip().lower()
		if key not in mapping:
			raise ValueError(f"Unsupported ML risk category: {category}")
		return mapping[key]


class MLInputMapperAdapter:
	"""Adapter that wraps MLInputMapper to conform to MLInputAdapter protocol."""

	def __init__(self):
		self.mapper = MLInputMapper()

	def prepare(self, assessment_data: Mapping[str, Any]) -> Any:
		"""Convert assessment data using authoritative ML input mapper."""
		try:
			return self.mapper.map_assessment_data(assessment_data)
		except MLInputValidationError as exc:
			# Wrap mapper errors in ValueError for backward compatibility
			raise ValueError(str(exc)) from exc


class PredictionService:
	def __init__(
		self,
		predictor: MLPredictor | None = None,
		input_adapter: MLInputAdapter | None = None,
		output_adapter: MLOutputAdapter | None = None,
	):
		self.predictor = predictor or UnavailableMLPredictor()
		self.input_adapter = input_adapter
		if self.input_adapter is None and isinstance(self.predictor, (UnavailableMLPredictor, RealFinpathPredictor)):
			self.input_adapter = MLInputMapperAdapter()
		self.output_adapter = output_adapter or PredictionOutputAdapter()

	@staticmethod
	def _persist_recommendations(db: Session, prediction: Prediction, model_output: Any) -> None:
		if not isinstance(model_output, Mapping):
			return
		recommendations = model_output.get("recommendations")
		if not isinstance(recommendations, Iterable) or isinstance(recommendations, (str, bytes)):
			return
		for index, text in enumerate(recommendations, start=1):
			if not text:
				continue
			record = Recommendation(
				prediction_id=prediction.id,
				category="ml_recommendation",
				recommendation_text=str(text),
				priority=min(index, 5),
			)
			db.add(record)

	def generate_and_store(
		self, db: Session, assessment: Assessment, user: User
	) -> Prediction:
		if assessment.user_id != user.id:
			raise LookupError("Assessment not found")
		if assessment.assessment_status != "completed":
			raise ValueError("Assessment must be completed before prediction")

		if self.input_adapter is not None:
			try:
				model_input = self.input_adapter.prepare(assessment.assessment_data or {})
			except ValueError as exc:
				raise PredictionUnavailableError(
					"The FINPATH prediction model is unavailable for the provided assessment data"
				) from exc
		else:
			model_input = assessment.assessment_data or {}
		raw_output = self.predictor.predict(model_input)
		result = self.output_adapter.validate(raw_output, assessment.id)
		values = result.model_dump(exclude={"assessment_id"}, exclude_none=True)
		if values.get("prediction_timestamp") is None:
			values["prediction_timestamp"] = datetime.now(timezone.utc)
		prediction = Prediction(assessment_id=assessment.id, **values)
		db.add(prediction)
		db.flush()
		self._persist_recommendations(db, prediction, raw_output)
		db.commit()
		db.refresh(prediction)
		return prediction


def get_user_prediction(db: Session, prediction_id: int, user: User) -> Prediction | None:
	return (
		db.query(Prediction)
		.join(Assessment, Prediction.assessment_id == Assessment.id)
		.filter(Prediction.id == prediction_id, Assessment.user_id == user.id)
		.first()
	)


def get_user_assessment_predictions(
	db: Session, assessment_id: int, user: User
) -> list[Prediction]:
	return (
		db.query(Prediction)
		.join(Assessment, Prediction.assessment_id == Assessment.id)
		.filter(Prediction.assessment_id == assessment_id, Assessment.user_id == user.id)
		.order_by(Prediction.created_at.desc())
		.all()
	)

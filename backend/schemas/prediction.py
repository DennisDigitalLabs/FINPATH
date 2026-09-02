from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


RiskLevel = Literal["low", "medium", "high"]


class PredictionRequest(BaseModel):
	"""Request to generate a prediction for an owned assessment."""

	model_config = ConfigDict(extra="forbid")

	assessment_id: int = Field(gt=0)


class PredictionCreate(BaseModel):
	"""Validated ML output, intended for the internal integration layer."""

	model_config = ConfigDict(extra="forbid")

	assessment_id: int = Field(gt=0)
	risk_level: RiskLevel
	risk_category: str = Field(min_length=1, max_length=255)
	probability: float = Field(ge=0, le=1)
	confidence: float | None = Field(default=None, ge=0, le=1)
	explanation: str = Field(min_length=1)
	contributing_factors: dict[str, Any] | None = None
	model_version: str = Field(min_length=1, max_length=50)
	prediction_timestamp: datetime | None = None

	@field_validator("risk_category", "explanation", "model_version")
	@classmethod
	def validate_text(cls, value: str) -> str:
		value = value.strip()
		if not value:
			raise ValueError("value cannot be blank")
		return value


class PredictionResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	assessment_id: int
	risk_level: RiskLevel
	risk_category: str
	probability: float
	confidence: float | None = None
	explanation: str
	contributing_factors: dict[str, Any] | None = None
	model_version: str
	prediction_timestamp: datetime
	created_at: datetime

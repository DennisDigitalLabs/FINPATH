from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecommendationCreate(BaseModel):
	model_config = ConfigDict(extra="forbid")

	prediction_id: int = Field(gt=0)
	category: str = Field(min_length=1, max_length=100)
	recommendation_text: str = Field(min_length=1)
	priority: int = Field(default=3, ge=1, le=5)

	@field_validator("category", "recommendation_text")
	@classmethod
	def validate_text(cls, value: str) -> str:
		value = value.strip()
		if not value:
			raise ValueError("value cannot be blank")
		return value


class RecommendationUpdate(BaseModel):
	model_config = ConfigDict(extra="forbid")

	category: str | None = Field(default=None, min_length=1, max_length=100)
	recommendation_text: str | None = Field(default=None, min_length=1)
	priority: int | None = Field(default=None, ge=1, le=5)

	@field_validator("category", "recommendation_text")
	@classmethod
	def validate_text(cls, value: str | None) -> str | None:
		if value is None:
			return value
		value = value.strip()
		if not value:
			raise ValueError("value cannot be blank")
		return value


class RecommendationResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	prediction_id: int
	category: str
	recommendation_text: str
	priority: int
	created_at: datetime

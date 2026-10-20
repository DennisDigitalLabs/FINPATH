from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


AssessmentStatus = Literal["draft", "completed"]


class AssessmentCreate(BaseModel):
	"""Assessment input owned by the authenticated user."""

	model_config = ConfigDict(extra="forbid")

	assessment_data: dict[str, Any] = Field(default_factory=dict)
	assessment_status: AssessmentStatus = "draft"

	@field_validator("assessment_status", mode="before")
	@classmethod
	def normalize_status(cls, value: str) -> str:
		return value.strip().lower() if isinstance(value, str) else value
	assessment_date: datetime | None = None

class AssessmentUpdate(BaseModel):
	model_config = ConfigDict(extra="forbid")

	assessment_data: dict[str, Any] | None = None
	assessment_status: AssessmentStatus | None = None
	assessment_date: datetime | None = None

	@field_validator("assessment_status", mode="before")
	@classmethod
	def normalize_status(cls, value: str | None) -> str | None:
		return value.strip().lower() if isinstance(value, str) else value

class AssessmentResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	user_id: int
	assessment_status: str
	assessment_data: dict[str, Any] | None = None
	assessment_date: datetime
	created_at: datetime
	updated_at: datetime

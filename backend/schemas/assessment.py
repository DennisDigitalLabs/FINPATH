import math
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import (
	BaseModel,
	ConfigDict,
	Field,
	StrictBool,
	StrictFloat,
	StrictInt,
	StrictStr,
	StringConstraints,
	field_validator,
)


AssessmentStatus = Literal["draft", "completed"]
AssessmentField = Literal[
	"age_range",
	"sex",
	"county",
	"education",
	"marital_status",
	"location_type",
	"household_size",
	"employment_status",
	"monthly_income",
	"income_reliability",
	"monthly_expenses",
	"financial_dependents",
	"bill_pressure",
	"savings_usage",
	"emergency_savings",
	"saves_regularly",
	"budgeting",
	"loan_usage",
	"loan_formal",
	"loan_informal",
	"digital_credit_usage",
	"loan_app_2",
	"loan_fuliza_2",
	"defaulted",
	"debt_repayment",
	"credit_barrier",
	"account_access",
	"service_distance",
	"digital_confidence",
	"chama_usage",
	"sacco_use",
	"mobile_money_use",
	"S7_2",
	"experienced_shock",
	"accessto_13k_1month",
	"CountLivelihood",
	"financial_confidence",
	"financial_literacy_score",
	"financial_information",
	"future_goal",
]
AssessmentValue = (
	Annotated[StrictStr, StringConstraints(max_length=500)]
	| StrictInt
	| StrictFloat
	| StrictBool
	| None
)
AssessmentData = dict[AssessmentField, AssessmentValue]

_NUMERIC_RANGES = {
	"monthly_income": (Decimal("0"), None, False),
	"monthly_expenses": (Decimal("0"), None, False),
	"household_size": (Decimal("1"), Decimal("30"), True),
	"financial_dependents": (Decimal("0"), Decimal("30"), True),
	"CountLivelihood": (Decimal("1"), Decimal("10"), True),
}


def validate_assessment_data(value: AssessmentData | None) -> AssessmentData | None:
	if value is None:
		return None
	for field, field_value in value.items():
		if isinstance(field_value, float) and not math.isfinite(field_value):
			raise ValueError(f"{field} must be finite")
		rule = _NUMERIC_RANGES.get(field)
		if rule is None or field_value is None:
			continue
		if isinstance(field_value, bool):
			raise ValueError(f"{field} must be numeric")
		try:
			number = Decimal(str(field_value))
		except InvalidOperation as exc:
			raise ValueError(f"{field} must be numeric") from exc
		if not number.is_finite():
			raise ValueError(f"{field} must be finite")
		minimum, maximum, integer_only = rule
		if number < minimum or (maximum is not None and number > maximum):
			raise ValueError(f"{field} is outside the supported range")
		if integer_only and number != number.to_integral_value():
			raise ValueError(f"{field} must be a whole number")
	return value


class AssessmentCreate(BaseModel):
	"""Assessment input owned by the authenticated user."""

	model_config = ConfigDict(extra="forbid")

	assessment_data: AssessmentData = Field(default_factory=dict, max_length=64)
	assessment_status: AssessmentStatus = "draft"

	@field_validator("assessment_status", mode="before")
	@classmethod
	def normalize_status(cls, value: str) -> str:
		return value.strip().lower() if isinstance(value, str) else value
	assessment_date: datetime | None = None

	@field_validator("assessment_data")
	@classmethod
	def validate_data(cls, value: AssessmentData) -> AssessmentData:
		return validate_assessment_data(value) or {}


class AssessmentUpdate(BaseModel):
	model_config = ConfigDict(extra="forbid")

	assessment_data: AssessmentData | None = Field(default=None, max_length=64)
	assessment_status: AssessmentStatus | None = None
	assessment_date: datetime | None = None

	@field_validator("assessment_status", mode="before")
	@classmethod
	def normalize_status(cls, value: str | None) -> str | None:
		return value.strip().lower() if isinstance(value, str) else value

	@field_validator("assessment_data")
	@classmethod
	def validate_data(cls, value: AssessmentData | None) -> AssessmentData | None:
		return validate_assessment_data(value)


class AssessmentResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	user_id: int
	assessment_status: str
	assessment_data: dict[str, Any] | None = None
	assessment_date: datetime
	created_at: datetime
	updated_at: datetime

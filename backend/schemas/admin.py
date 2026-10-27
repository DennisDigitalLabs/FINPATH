from datetime import datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StrictBool

from backend.schemas.user import AdminCreate, UserCreate


class AdminBootstrapCreate(AdminCreate):
	"""First-owner details plus the backend-configured bootstrap secret."""

	bootstrap_token: str = Field(min_length=1, max_length=4096)
	confirm_existing_owner: bool = False


class AdminBootstrapStatus(BaseModel):
	model_config = ConfigDict(extra="forbid")

	setup_available: bool
	administrator_exists: bool
	setup_configured: bool


class AdminManagedUserCreate(UserCreate):
	"""Validated details for an admin-created standard user account."""


class AdminUserResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	full_name: str
	email: EmailStr
	role: str
	is_active: StrictBool
	created_at: datetime
	updated_at: datetime


class AdminUserListResponse(BaseModel):
	model_config = ConfigDict(extra="forbid")

	items: list[AdminUserResponse]
	total: int
	page: int
	page_size: int


AdminRecordType = Literal["assessments", "predictions", "recommendations"]


class AdminRecordResponse(BaseModel):
	model_config = ConfigDict(extra="forbid")

	id: int
	user_id: int
	full_name: str
	email: EmailStr
	created_at: datetime
	status: str | None = None
	assessment_id: int | None = None
	risk_level: str | None = None
	risk_category: str | None = None
	probability: float | None = None
	model_version: str | None = None
	prediction_id: int | None = None
	category: str | None = None
	priority: int | None = None
	recommendation_text: str | None = None


class AdminRecordListResponse(BaseModel):
	model_config = ConfigDict(extra="forbid")

	record_type: AdminRecordType
	items: list[AdminRecordResponse]
	total: int
	page: int
	page_size: int


class AdminUserStatusUpdate(BaseModel):
	model_config = ConfigDict(extra="forbid")

	is_active: StrictBool


class AdminHealthResponse(BaseModel):
	model_config = ConfigDict(extra="forbid")

	status: str
	database: str
	checked_at: datetime


class AdminModelMonitoringResponse(BaseModel):
	model_config = ConfigDict(extra="forbid")

	model_available: StrictBool
	model_version: str | None
	recorded_prediction_count: int
	recorded_model_versions: dict[str, int]
	explanation_available_count: int
	contributing_factors_available_count: int
	generated_at: datetime


class AdminAuditLogResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True, extra="forbid")

	id: int
	actor_user_id: int | None
	action: str
	target_type: str | None
	target_id: str | None
	outcome: Literal["success", "failure", "unknown"]
	created_at: datetime


class AdminAuditLogListResponse(BaseModel):
	model_config = ConfigDict(extra="forbid")

	items: list[AdminAuditLogResponse]
	total: int
	page: int
	page_size: int


class AdminOperationalEventResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True, extra="forbid")

	id: int
	event_type: str
	source: str
	severity: str
	summary: str
	status: str
	occurred_at: datetime
	acknowledged_at: datetime | None
	acknowledged_by_user_id: int | None


class AdminOperationalEventListResponse(BaseModel):
	model_config = ConfigDict(extra="forbid")

	items: list[AdminOperationalEventResponse]
	total: int
	page: int
	page_size: int


class AdminOperationalSummaryResponse(BaseModel):
	model_config = ConfigDict(extra="forbid")

	recorded_error_count: int
	open_alert_count: int
	generated_at: datetime

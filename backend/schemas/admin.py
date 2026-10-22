from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, StrictBool

from backend.schemas.user import UserCreate


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


class AdminUserStatusUpdate(BaseModel):
	model_config = ConfigDict(extra="forbid")

	is_active: StrictBool


class AdminHealthResponse(BaseModel):
	model_config = ConfigDict(extra="forbid")

	status: str
	database: str
	checked_at: datetime

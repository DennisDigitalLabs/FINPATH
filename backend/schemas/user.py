from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
	"""Public fields accepted when creating a standard user account."""

	model_config = ConfigDict(extra="forbid")

	full_name: str = Field(min_length=1, max_length=255)
	email: EmailStr
	password: str = Field(min_length=8, max_length=128)

	@field_validator("full_name")
	@classmethod
	def validate_full_name(cls, value: str) -> str:
		value = value.strip()
		if not value:
			raise ValueError("full_name cannot be blank")
		return value

	@field_validator("password")
	@classmethod
	def validate_password(cls, value: str) -> str:
		if value != value.strip():
			raise ValueError("password cannot start or end with whitespace")
		if not any(character.isalpha() for character in value):
			raise ValueError("password must contain at least one letter")
		if not any(character.isdigit() for character in value):
			raise ValueError("password must contain at least one number")
		return value


class UserUpdate(BaseModel):
	"""Optional user-editable account fields."""

	model_config = ConfigDict(extra="forbid")

	full_name: str | None = Field(default=None, min_length=1, max_length=255)
	email: EmailStr | None = None
	password: str | None = Field(default=None, min_length=8, max_length=128)
	is_active: bool | None = None

	@field_validator("full_name")
	@classmethod
	def validate_full_name(cls, value: str | None) -> str | None:
		if value is None:
			return value
		value = value.strip()
		if not value:
			raise ValueError("full_name cannot be blank")
		return value

	@field_validator("password")
	@classmethod
	def validate_password(cls, value: str | None) -> str | None:
		if value is None:
			return value
		if value != value.strip():
			raise ValueError("password cannot start or end with whitespace")
		if not any(character.isalpha() for character in value):
			raise ValueError("password must contain at least one letter")
		if not any(character.isdigit() for character in value):
			raise ValueError("password must contain at least one number")
		return value


class UserLogin(BaseModel):
	model_config = ConfigDict(extra="forbid")

	email: EmailStr
	password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	full_name: str
	email: EmailStr
	role: str
	is_active: bool
	created_at: datetime
	updated_at: datetime


class TokenResponse(BaseModel):
	access_token: str
	token_type: str = "bearer"

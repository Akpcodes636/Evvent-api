from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from model.user import UserRole

SELF_REGISTERABLE_ROLES = {UserRole.user, UserRole.organizer}


class RegisterRequest(BaseModel):
    email: EmailStr = Field(
        examples=["john@example.com"]
    )
    first_name: str = Field(
        min_length=1,
        max_length=100,
        examples=["John"]
    )
    last_name: str = Field(
        min_length=1,
        max_length=100,
        examples=["Doe"]
    )
    phone: str = Field(
        min_length=1,
        max_length=32,
        examples=["+2348012345678"]
    )
    password: str = Field(
        min_length=8,
        max_length=128,
        examples=["Password123!"]
    )
    role: UserRole = Field(default=UserRole.user, examples=["user"])
    organization: str | None = Field(default=None, max_length=200, examples=["Acme Events Co."])

    @model_validator(mode="after")
    def _validate_role_and_organization(self):
        if self.role not in SELF_REGISTERABLE_ROLES:
            raise ValueError("role must be either 'user' or 'organizer'")
        if self.role == UserRole.organizer and not self.organization:
            raise ValueError("organization is required when registering as an organizer")
        return self
print(RegisterRequest.model_json_schema())


class AdminRegisterRequest(BaseModel):
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UpdateProfileRequest(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=1, max_length=32)
    organization: str | None = Field(default=None, max_length=200)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class BankDetailsRequest(BaseModel):
    bank_name: str = Field(min_length=1, max_length=100)
    bank_account_number: str = Field(min_length=1, max_length=34)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None = None
    organization: str | None = None
    bank_name: str | None = None
    bank_account_number: str | None = None
    role: UserRole
    created_at: datetime


class MessageResponse(BaseModel):
    status: str = "success"
    message: str


class LoginResponse(MessageResponse):
    access_token: str
    token_type: str = "bearer"


class ForgotPasswordResponse(MessageResponse):
    reset_token: str | None = None

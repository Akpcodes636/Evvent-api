from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from model.user import UserRole

SELF_REGISTERABLE_ROLES = {UserRole.user, UserRole.organizer}

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
    confirm_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def _validate_passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("new_password and confirm_password do not match")
        return self


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

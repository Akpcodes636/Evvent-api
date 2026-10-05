from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from model.user import AccountType

SELF_REGISTERABLE_TYPES = {AccountType.individual, AccountType.organization}


class RegisterRequest(BaseModel):
    email: EmailStr = Field(examples=["john@example.com"])
    first_name: str = Field(min_length=1, max_length=100, examples=["John"])
    last_name: str = Field(min_length=1, max_length=100, examples=["Doe"])
    phone: str = Field(min_length=1, max_length=32, examples=["+2348012345678"])
    password: str = Field(min_length=8, max_length=128, examples=["Password123!"])
    account_type: AccountType = Field(
        description="Choose 'individual' for a personal account or 'organization' for a registered business account.",
        examples=["individual"],
    )
    organization: str | None = Field(
        default=None,
        max_length=200,
        description="Business name. Required when account_type is 'organization'.",
        examples=["Acme Events Co."],
    )
    category_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self):
        if self.account_type not in SELF_REGISTERABLE_TYPES:
            raise ValueError("account_type must be 'individual' or 'organization'")
        if self.account_type == AccountType.organization and not self.organization:
            raise ValueError("organization (business name) is required for organization accounts")
        return self


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
    account_type: AccountType
    organization: str | None = None
    bank_name: str | None = None
    bank_account_number: str | None = None
    created_at: datetime


class MessageResponse(BaseModel):
    status: str = "success"
    message: str


class LoginResponse(MessageResponse):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=512)


class ForgotPasswordResponse(MessageResponse):
    pass


class UpdatePreferencesRequest(BaseModel):
    category_ids: list[UUID] = Field(default_factory=list)

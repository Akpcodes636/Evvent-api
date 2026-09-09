from datetime import datetime
from enum import Enum
import uuid

from sqlalchemy import Column, DateTime, Enum as SqlEnum, String
from sqlmodel import Field, SQLModel


class UserRole(str, Enum):
    admin = "admin"
    organizer = "organizer"
    user = "user"


class User(SQLModel, table=True):
    __tablename__ = "users"

    uuid: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    email: str = Field(sa_column=Column(String(320), unique=True, nullable=False, index=True))
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    role: UserRole = Field(
        default=UserRole.user,
        sa_column=Column(SqlEnum(UserRole, name="user_role_enum"), nullable=False, index=True),
    )
    phone: str | None = Field(default=None, max_length=32)
    organization: str | None = Field(default=None, max_length=200)
    bank_name: str | None = Field(default=None, max_length=100)
    bank_account_number: str | None = Field(default=None, max_length=34)
    password_hash: str = Field(exclude=True, max_length=512)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, nullable=False, onupdate=datetime.utcnow),
    )


class PasswordResetToken(SQLModel, table=True):
    __tablename__ = "password_reset_tokens"

    uuid: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="users.uuid", index=True)
    token: str = Field(index=True, unique=True, max_length=128)
    expires_at: datetime = Field(sa_column=Column(DateTime, nullable=False))
    used_at: datetime | None = Field(default=None, sa_column=Column(DateTime, nullable=True))

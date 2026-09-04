from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from auth.dependencies import get_current_user
from auth.schema import (
    ForgotPasswordRequest, ForgotPasswordResponse, LoginRequest, LoginResponse,
    MessageResponse, RegisterRequest, ResetPasswordRequest, UserResponse,
)
from auth.services import authenticate_user, create_reset_token, register_user, reset_password
from core.security import create_access_token
from database.session import get_session
from logger import logger
from model.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/", response_model=MessageResponse)
def auth_root() -> MessageResponse:
    return MessageResponse(message="Welcome to the authentication API")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, session: Session = Depends(get_session)) -> UserResponse:
    user = register_user(session, **data.model_dump())
    logger.info("Registered new user %s (%s)", user.uuid, user.email)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, session: Session = Depends(get_session)) -> LoginResponse:
    user = authenticate_user(session, **data.model_dump())
    logger.info("User %s (%s) logged in", user.uuid, user.email)
    return LoginResponse(message="Login successful", access_token=create_access_token(user.uuid))


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(data: ForgotPasswordRequest, session: Session = Depends(get_session)) -> ForgotPasswordResponse:
    token = create_reset_token(session, email=str(data.email))
    logger.info("Password reset requested for %s (token issued: %s)", data.email, token is not None)
    return ForgotPasswordResponse(
        message="If an account exists, password reset instructions have been created.",
        reset_token=token,
    )


@router.patch("/reset-password", response_model=MessageResponse)
def reset_password_endpoint(data: ResetPasswordRequest, session: Session = Depends(get_session)) -> MessageResponse:
    reset_password(session, **data.model_dump())
    logger.info("Password reset completed for token %s...", data.token[:8])
    return MessageResponse(message="Password reset successful")




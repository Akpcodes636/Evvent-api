from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlmodel import Session

from auth.dependencies import get_current_user, require_roles
from auth.schema import (
    AdminRegisterRequest, BankDetailsRequest, ChangePasswordRequest,
    ForgotPasswordRequest, ForgotPasswordResponse, LoginRequest, LoginResponse,
    MessageResponse, RegisterRequest, ResetPasswordRequest, UpdateProfileRequest, UserResponse,
)
from auth.services import (
    authenticate_user, change_password, create_reset_token, register_user,
    reset_password, update_bank_details, update_profile,
)
from core.config import settings
from core.security import create_access_token
from database.session import get_session
from logger import logger
from model.user import User, UserRole
from utils.email import send_password_reset_email, send_welcome_email

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/", response_model=MessageResponse)
def auth_root() -> MessageResponse:
    return MessageResponse(message="Welcome to the authentication API")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    data: RegisterRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
) -> UserResponse:
    user = register_user(session, **data.model_dump())
    logger.info("Registered new %s %s (%s)", user.role, user.uuid, user.email)
    background_tasks.add_task(send_welcome_email, user.email, user.first_name)
    return UserResponse.model_validate(user)


@router.post("/admin/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_admin(
    data: AdminRegisterRequest,
    session: Session = Depends(get_session),
    _: User = Depends(require_roles(UserRole.admin)),
) -> UserResponse:
    user = register_user(session, **data.model_dump(), role=UserRole.admin)
    logger.info("Registered new admin %s (%s)", user.uuid, user.email)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, session: Session = Depends(get_session)) -> LoginResponse:
    user = authenticate_user(session, **data.model_dump())
    logger.info("User %s (%s) logged in", user.uuid, user.email)
    return LoginResponse(message="Login successful", access_token=create_access_token(user.uuid))


@router.post("/logout", response_model=MessageResponse)
def logout(current_user: User = Depends(get_current_user)) -> MessageResponse:
    logger.info("User %s (%s) logged out", current_user.uuid, current_user.email)
    return MessageResponse(message="Logout successful")


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
def update_current_user(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> UserResponse:
    user = update_profile(session, current_user, **data.model_dump())
    logger.info("User %s updated their profile", user.uuid)
    return UserResponse.model_validate(user)


@router.patch("/me/password", response_model=MessageResponse)
def update_current_user_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MessageResponse:
    change_password(session, current_user, **data.model_dump())
    logger.info("User %s changed their password", current_user.uuid)
    return MessageResponse(message="Password updated successfully")


@router.patch("/me/bank-details", response_model=UserResponse)
def update_current_user_bank_details(
    data: BankDetailsRequest,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.organizer)),
    session: Session = Depends(get_session),
) -> UserResponse:
    user = update_bank_details(session, current_user, **data.model_dump())
    logger.info("User %s updated their bank details", user.uuid)
    return UserResponse.model_validate(user)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
) -> ForgotPasswordResponse:
    user, token = create_reset_token(session, email=str(data.email))
    logger.info("Password reset requested for %s (token issued: %s)", data.email, token is not None)
    if user and token:
        background_tasks.add_task(
            send_password_reset_email,
            user.email,
            user.first_name,
            token,
            settings.RESET_TOKEN_EXPIRES_MINUTES,
        )
    return ForgotPasswordResponse(
        message="If an account exists, password reset instructions have been created and sent to your email",
        reset_token=token,
    )


@router.patch("/reset-password", response_model=MessageResponse)
def reset_password_endpoint(data: ResetPasswordRequest, session: Session = Depends(get_session)) -> MessageResponse:
    reset_password(session, token=data.token, new_password=data.new_password)
    logger.info("Password reset completed for token %s...", data.token[:8])
    return MessageResponse(message="Password reset successful")

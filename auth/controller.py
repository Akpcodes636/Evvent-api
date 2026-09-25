from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlmodel import Session

from auth.dependencies import get_current_user, require_roles
from auth.schema import (
    AdminRegisterRequest, BankDetailsRequest, ChangePasswordRequest,
    ForgotPasswordRequest, ForgotPasswordResponse, LoginRequest, LoginResponse,
    MessageResponse, RefreshTokenRequest, RegisterRequest, ResetPasswordRequest, SwitchRoleRequest,
    UpdatePreferencesRequest, UpdateProfileRequest, UserResponse,
)
from auth.services import (
    authenticate_user, bootstrap_admin, change_password, create_refresh_token, create_reset_token,
    refresh_access_token, register_user, reset_password, revoke_refresh_token, switch_user_role,
    update_bank_details, update_profile,
)
from core.config import settings
from core.security import create_access_token
from database.session import get_session
from event.schema import CategoryResponse
from event.services import get_user_category_preferences, set_user_category_preferences
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


@router.post("/admin/bootstrap", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def bootstrap_admin_endpoint(
    data: AdminRegisterRequest,
    session: Session = Depends(get_session),
) -> UserResponse:
    """Create the first admin account. Fails once any admin already exists."""
    user = bootstrap_admin(session, **data.model_dump())
    logger.info("Bootstrapped first admin %s (%s)", user.uuid, user.email)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, session: Session = Depends(get_session)) -> LoginResponse:
    user = authenticate_user(session, **data.model_dump())
    access_token = create_access_token(user.uuid)
    refresh_token = create_refresh_token(session, user)
    logger.info("User %s (%s) logged in", user.uuid, user.email)
    return LoginResponse(message="Login successful", access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", response_model=MessageResponse)
def logout(data: RefreshTokenRequest, session: Session = Depends(get_session)) -> MessageResponse:
    revoke_refresh_token(session, data.refresh_token)
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
    )


@router.patch("/reset-password", response_model=MessageResponse)
def reset_password_endpoint(data: ResetPasswordRequest, session: Session = Depends(get_session)) -> MessageResponse:
    reset_password(session, token=data.token, new_password=data.new_password)
    logger.info("Password reset completed for token %s...", data.token[:8])
    return MessageResponse(message="Password reset successful")


@router.get("/me/preferences", response_model=list[CategoryResponse])
def get_current_user_preferences(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[CategoryResponse]:
    categories = get_user_category_preferences(session, current_user)
    return [CategoryResponse.model_validate(c) for c in categories]


@router.put("/me/preferences", response_model=list[CategoryResponse])
def update_current_user_preferences(
    data: UpdatePreferencesRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[CategoryResponse]:
    categories = set_user_category_preferences(session, current_user, data.category_ids)
    logger.info("User %s set %d event category preference(s)", current_user.uuid, len(categories))
    return [CategoryResponse.model_validate(c) for c in categories]


@router.patch("/me/role", response_model=UserResponse)
def switch_role(
    data: SwitchRoleRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> UserResponse:
    user = switch_user_role(session, current_user, role=data.role)
    logger.info("User %s switched role to %s", user.uuid, user.role)
    return UserResponse.model_validate(user)


@router.post("/refresh", response_model=LoginResponse)
def refresh(data: RefreshTokenRequest, session: Session = Depends(get_session)) -> LoginResponse:
    access_token, new_refresh_token = refresh_access_token(session, data.refresh_token)
    return LoginResponse(
        message="Token refreshed successfully",
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.get("/protected", response_model=MessageResponse)
def protected_route(current_user: User = Depends(get_current_user)) -> MessageResponse:
    return MessageResponse(message=f"Hello, {current_user.first_name} | You accessed a protected route")


@router.get("/organizer/dashboard", response_model=MessageResponse)
def organizer_dashboard(_: User = Depends(require_roles(UserRole.organizer))) -> MessageResponse:
    return MessageResponse(message="Organizer dashboard")


@router.get("/organizer/test")
def organizer_test(current_user: User = Depends(require_roles(UserRole.organizer, UserRole.admin))):
    return {
        "message": "You have organizer permissions",
        "user": str(current_user.uuid),
        "role": current_user.role,
    }

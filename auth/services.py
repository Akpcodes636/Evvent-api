from datetime import datetime, timedelta
import hashlib
import hmac
import secrets
from uuid import UUID

from fastapi import HTTPException, status
from sqlmodel import Session, select

from core.config import settings
from core.security import create_access_token
from event.services import set_user_category_preferences
from logger import logger
from model.user import PasswordResetToken, RefreshToken, User, UserRole


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"{salt.hex()}${digest.hex()}"


def _password_matches(password: str, stored_hash: str) -> bool:
    salt_hex, digest_hex = stored_hash.split("$", maxsplit=1)
    calculated = _hash_password(password, bytes.fromhex(salt_hex)).split("$", maxsplit=1)[1]
    return hmac.compare_digest(calculated, digest_hex)


def register_user(
    session: Session,
    *,
    email: str,
    first_name: str,
    last_name: str,
    phone: str,
    password: str,
    role: UserRole = UserRole.user,
    organization: str | None = None,
    category_ids: list[UUID] | None = None,
) -> User:
    email = email.lower()
    if session.exec(select(User).where(User.email == email)).first():
        logger.warning("Registration attempted for existing email %s", email)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account already exists for this email")
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        role=role,
        organization=organization,
        password_hash=_hash_password(password),
    )
    session.add(user)
    if category_ids:
        # Commits together with the user, so an unknown category id doesn't leave a half-registered account.
        set_user_category_preferences(session, user, category_ids)
    session.commit()
    session.refresh(user)
    return user


def bootstrap_admin(
    session: Session,
    *,
    email: str,
    first_name: str,
    last_name: str,
    phone: str,
    password: str,
) -> User:
    """Create the first admin account. Only works while no admin exists yet."""
    if session.exec(select(User).where(User.role == UserRole.admin)).first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="An admin already exists; ask an existing admin to register new admins",
        )
    return register_user(
        session,
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        password=password,
        role=UserRole.admin,
    )


def authenticate_user(session: Session, *, email: str, password: str) -> User:
    user = session.exec(select(User).where(User.email == email.lower())).first()
    if not user or not _password_matches(password, user.password_hash):
        logger.warning("Failed login attempt for %s", email.lower())
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return user


def create_reset_token(session: Session, *, email: str) -> tuple[User, str] | tuple[None, None]:
    user = session.exec(select(User).where(User.email == email.lower())).first()
    if not user:
        return None, None
    token = secrets.token_urlsafe(32)
    session.add(PasswordResetToken(
        user_id=user.uuid,
        token=token,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.RESET_TOKEN_EXPIRES_MINUTES),
    ))
    session.commit()
    return user, token


def reset_password(session: Session, *, token: str, new_password: str) -> None:
    reset = session.exec(select(PasswordResetToken).where(PasswordResetToken.token == token)).first()
    if not reset or reset.used_at or reset.expires_at < datetime.utcnow():
        logger.warning("Invalid or expired password reset token used")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    user = session.get(User, reset.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token")
    user.password_hash = _hash_password(new_password)
    user.updated_at = datetime.utcnow()
    reset.used_at = datetime.utcnow()
    session.add(user)
    session.add(reset)
    _revoke_user_refresh_tokens(session, user)
    session.commit()


def switch_user_role(
    session: Session,
    user: User,
    *,
    role: UserRole,
) -> User:

    if user.role == UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin accounts cannot switch roles",
        )

    if role not in {
        UserRole.user,
        UserRole.organizer,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid role switch",
        )

    user.role = role
    user.updated_at = datetime.utcnow()

    session.add(user)
    session.commit()
    session.refresh(user)

    return user

def update_profile(
    session: Session,
    user: User,
    *,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    organization: str | None = None,
) -> User:
    if email is not None:
        email = email.lower()
        if email != user.email and session.exec(select(User).where(User.email == email)).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account already exists for this email")
        user.email = email
    if first_name is not None:
        user.first_name = first_name
    if last_name is not None:
        user.last_name = last_name
    if phone is not None:
        user.phone = phone
    if organization is not None:
        user.organization = organization
    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def change_password(session: Session, user: User, *, current_password: str, new_password: str) -> None:
    if not _password_matches(current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")
    user.password_hash = _hash_password(new_password)
    user.updated_at = datetime.utcnow()
    session.add(user)
    _revoke_user_refresh_tokens(session, user)
    session.commit()


def update_bank_details(session: Session, user: User, *, bank_name: str, bank_account_number: str) -> User:
    user.bank_name = bank_name
    user.bank_account_number = bank_account_number
    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _revoke_user_refresh_tokens(session: Session, user: User) -> None:
    now = datetime.utcnow()
    for token in session.exec(
        select(RefreshToken).where(RefreshToken.user_id == user.uuid, RefreshToken.revoked_at.is_(None))
    ).all():
        token.revoked_at = now
        session.add(token)


def revoke_refresh_token(session: Session, raw_refresh_token: str) -> None:
    token_hash = _hash_refresh_token(raw_refresh_token)
    refresh_token = session.exec(select(RefreshToken).where(RefreshToken.token_hash == token_hash)).first()
    if refresh_token and refresh_token.revoked_at is None:
        refresh_token.revoked_at = datetime.utcnow()
        session.add(refresh_token)
        session.commit()

def create_refresh_token (
        session:Session,
        user:User,
)-> str:

    raw_token = secrets.token_urlsafe(64)

    token_hash = _hash_refresh_token(raw_token)

    refresh_token = RefreshToken(
        user_id = user.uuid,
        token_hash=token_hash,
        expires_at=datetime.utcnow()
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRES_DAYS),
    )

    session.add(refresh_token)
    session.commit()

    return raw_token

def refresh_access_token(
    session: Session,
    raw_refresh_token: str,
) -> tuple[str, str]:

    token_hash = _hash_refresh_token(raw_refresh_token)

    refresh_token = session.exec(
        select(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
    ).first()

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if refresh_token.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    if refresh_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
        )

    user = session.get(User, refresh_token.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )

    # Revoke old refresh token
    refresh_token.revoked_at = datetime.utcnow()

    session.add(refresh_token)
    session.commit()

    # Create new credentials
    new_access_token = create_access_token(user.uuid)

    new_refresh_token = create_refresh_token(
        session,
        user,
    )

    return new_access_token, new_refresh_token

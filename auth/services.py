from datetime import datetime, timedelta
import hashlib
import hmac
import secrets

from fastapi import HTTPException, status
from sqlmodel import Session, select

from core.config import settings
from logger import logger
from model.user import PasswordResetToken, User


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"{salt.hex()}${digest.hex()}"


def _password_matches(password: str, stored_hash: str) -> bool:
    salt_hex, digest_hex = stored_hash.split("$", maxsplit=1)
    calculated = _hash_password(password, bytes.fromhex(salt_hex)).split("$", maxsplit=1)[1]
    return hmac.compare_digest(calculated, digest_hex)


def register_user(session: Session, *, email: str, first_name: str, last_name: str, password: str,) -> User:
    email = email.lower()
    if session.exec(select(User).where(User.email == email)).first():
        logger.warning("Registration attempted for existing email %s", email)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account already exists for this email")
    user = User(email=email, first_name=first_name, last_name=last_name, password_hash=_hash_password(password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def authenticate_user(session: Session, *, email: str, password: str) -> User:
    user = session.exec(select(User).where(User.email == email.lower())).first()
    if not user or not _password_matches(password, user.password_hash):
        logger.warning("Failed login attempt for %s", email.lower())
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return user


def create_reset_token(session: Session, *, email: str) -> str | None:
    user = session.exec(select(User).where(User.email == email.lower())).first()
    if not user:
        return None
    token = secrets.token_urlsafe(32)
    session.add(PasswordResetToken(
        user_id=user.uuid,
        token=token,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.RESET_TOKEN_EXPIRES_MINUTES),
    ))
    session.commit()
    return token


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
    session.commit()

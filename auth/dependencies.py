from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from core.exceptions import AppError
from core.security import decode_access_token
from database.session import get_session
from logger import logger
from model.user import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> User:
    if credentials is None:
        raise AppError("Not authenticated", status_code=401)

    user_id = decode_access_token(credentials.credentials)
    user = session.get(User, user_id)
    if not user:
        logger.warning("Token valid but user %s no longer exists", user_id)
        raise AppError("Not authenticated", status_code=401)

    return user


def require_roles(*roles: UserRole):
    """Return a dependency that only allows users whose role is in ``roles``."""

    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            logger.warning("User %s with role %s denied access", current_user.uuid, current_user.role)
            raise AppError("You do not have permission to perform this action", status_code=403)
        return current_user

    return _check

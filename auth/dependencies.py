from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from core.exceptions import AppError
from core.security import decode_access_token
from database.session import get_session
from logger import logger
from model.user import AccountType, User

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


def require_roles(*account_types: AccountType):
    """Return a dependency that only allows users whose account_type is in ``account_types``."""

    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.account_type not in account_types:
            logger.warning(
                "User %s with account_type %s denied access",
                current_user.uuid,
                current_user.account_type,
            )
            raise AppError("You do not have permission to perform this action", status_code=403)
        return current_user

    return _check

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from core.exceptions import AppError
from core.security import decode_access_token
from database.session import get_session
from logger import logger
from model.user import User

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

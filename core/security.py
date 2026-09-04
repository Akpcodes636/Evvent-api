import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from uuid import UUID

from core.config import settings
from core.exceptions import AppError


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def create_access_token(user_id: UUID) -> str:
    """Create a compact HS256 bearer token for an authenticated user."""
    now = datetime.now(timezone.utc)
    header = _base64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _base64url(json.dumps({
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRES_MINUTES)).timestamp()),
    }, separators=(",", ":")).encode())
    signature = hmac.new(settings.JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    return f"{header}.{payload}.{_base64url(signature)}"


def decode_access_token(token: str) -> UUID:
    """Verify an HS256 bearer token's signature and expiry, returning the user id."""
    try:
        header, payload, signature = token.split(".")
    except ValueError:
        raise AppError("Invalid authentication token", status_code=401)

    expected_signature = hmac.new(
        settings.JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256
    ).digest()
    if not hmac.compare_digest(_base64url(expected_signature), signature):
        raise AppError("Invalid authentication token", status_code=401)

    try:
        claims = json.loads(_base64url_decode(payload))
        user_id = UUID(claims["sub"])
        expires_at = claims["exp"]
    except (ValueError, KeyError, json.JSONDecodeError):
        raise AppError("Invalid authentication token", status_code=401)

    if datetime.now(timezone.utc).timestamp() >= expires_at:
        raise AppError("Authentication token has expired", status_code=401)

    return user_id

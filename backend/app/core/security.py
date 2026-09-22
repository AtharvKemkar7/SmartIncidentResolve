import hashlib
import hmac
import time
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.core.config import settings
from app.core.errors import AUTH_INVALID, AUTH_REQUIRED
from app.models.auth import User


def _sign(payload: str) -> str:
    secret = settings.app_auth_secret.encode("utf-8")
    return hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def create_token(email: str) -> str:
    issued = int(time.time())
    payload = f"{email}|{issued}"
    return f"{payload}|{_sign(payload)}"


def parse_token(token: str) -> str | None:
    parts = token.split("|")
    if len(parts) != 3:
        return None
    email, issued, signature = parts
    payload = f"{email}|{issued}"
    expected = _sign(payload)
    if not hmac.compare_digest(signature, expected):
        return None
    return email


def authenticate(email: str, password: str) -> User:
    if (
        email.strip().lower() == settings.default_user_email.lower()
        and password == settings.default_user_password
    ):
        return User(email=settings.default_user_email, name="Demo Engineer")
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=AUTH_INVALID)


def get_current_user(authorization: Annotated[str | None, Header()] = None) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=AUTH_REQUIRED)
    token = authorization.split(" ", 1)[1].strip()
    email = parse_token(token)
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=AUTH_REQUIRED)
    return User(email=email, name="Demo Engineer")


CurrentUser = Annotated[User, Depends(get_current_user)]

import hashlib
import secrets
from typing import Annotated

from fastapi import Depends, Request, Security
from fastapi.security import APIKeyCookie, APIKeyHeader
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.errors import ApiError
from app.models import AuthSession, utcnow

passwords = PasswordHash.recommended()
dummy_hash = passwords.hash("dummy-password-for-timing")
cookie_scheme = APIKeyCookie(name="taskflow_session", auto_error=False)
csrf_scheme = APIKeyHeader(name="X-CSRF-Token", auto_error=False)
Db = Annotated[Session, Depends(get_db)]


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def current_session(db: Db, token: Annotated[str | None, Security(cookie_scheme)]):
    session = db.get(AuthSession, token_hash(token)) if token else None
    if session is None or session.expires_at <= utcnow():
        raise ApiError(401, "UNAUTHORIZED", "Authentication required or session expired")
    return session


CurrentSession = Annotated[AuthSession, Depends(current_session)]


def require_csrf(session: CurrentSession, token: Annotated[str | None, Security(csrf_scheme)]):
    if not token or not secrets.compare_digest(token, session.csrf_token):
        raise ApiError(403, "CSRF_INVALID", "Missing or invalid CSRF token")
    return session


def require_origin(request: Request):
    if request.headers.get("origin") not in settings.origins:
        raise ApiError(403, "ORIGIN_FORBIDDEN", "Missing or untrusted Origin")

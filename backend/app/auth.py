import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.errors import ApiError, ERROR_RESPONSES
from app.models import AuthSession, User, utcnow
from app.outbox import log_committed, stage_event
from app.schemas import Credentials, CsrfOut, UserOut
from app.security import (CurrentSession, Db, dummy_hash, passwords, require_csrf,
                          require_origin, token_hash)

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"], responses=ERROR_RESPONSES)


@router.post("/register", status_code=201, response_model=UserOut, dependencies=[Depends(require_origin)])
def register(body: Credentials, db: Db, request: Request):
    user = User(email=body.email, password_hash=passwords.hash(body.password))
    db.add(user)
    event = None
    try:
        if settings.notifications_enabled:
            db.flush()
            event = stage_event(db, "user.registered", user.id, request.state.correlation_id,
                                {"recipient_email": user.email})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, "EMAIL_EXISTS", "Email is already registered")
    log_committed(event)
    return user


@router.post("/login", response_model=UserOut, dependencies=[Depends(require_origin)])
def login(body: Credentials, response: Response, db: Db):
    user = db.scalar(select(User).where(User.email == body.email))
    valid = passwords.verify(body.password, user.password_hash if user else dummy_hash)
    if not user or not valid:
        raise ApiError(401, "INVALID_CREDENTIALS", "Invalid email or password")
    db.execute(delete(AuthSession).where(AuthSession.expires_at <= utcnow()))
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=token_hash(token), user_id=user.id,
                       csrf_token=secrets.token_urlsafe(32),
                       expires_at=utcnow() + timedelta(hours=settings.session_hours)))
    db.commit()
    response.set_cookie("taskflow_session", token, httponly=True, samesite="lax",
                        secure=settings.cookie_secure, max_age=settings.session_hours * 3600, path="/")
    response.headers["Cache-Control"] = "no-store"
    return user


@router.get("/me", response_model=UserOut)
def me(session: CurrentSession, db: Db):
    return db.get(User, session.user_id)


@router.get("/csrf", response_model=CsrfOut)
def csrf(session: CurrentSession, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {"csrf_token": session.csrf_token}


@router.post("/logout", status_code=204, dependencies=[Depends(require_csrf)])
def logout(session: CurrentSession, db: Db):
    db.delete(session)
    db.commit()
    response = Response(status_code=204)
    response.delete_cookie("taskflow_session", path="/", secure=settings.cookie_secure,
                           httponly=True, samesite="lax")
    return response

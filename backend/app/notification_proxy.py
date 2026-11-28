import logging
from contextlib import suppress
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from app.config import settings
from app.errors import ApiError, ErrorResponse
from app.outbox import log
from app.security import CurrentSession, require_csrf

router = APIRouter(
    prefix="/api/v1/notifications", tags=["Notifications"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 422, 503)},
)
mutation = [Depends(require_csrf)]


def forward(request, session, suffix=""):
    if not settings.notifications_enabled:
        raise ApiError(503, "NOTIFICATIONS_DISABLED", "Notifications are disabled")
    token = settings.internal_service_token.get_secret_value()
    url = f"{settings.notification_api_url.rstrip('/')}/api/v1/notifications{suffix}"
    correlation_id = str(request.state.correlation_id)
    try:
        timeout = httpx.Timeout(
            settings.notification_api_timeout,
            connect=settings.http_connect_timeout or settings.notification_api_timeout,
            read=settings.http_read_timeout or settings.notification_api_timeout,
        )
        with httpx.Client(timeout=timeout, trust_env=False) as client:
            result = client.request(
                request.method, url, params=list(request.query_params.multi_items()),
                headers={"X-Service-Token": token, "X-User-ID": str(session.user_id),
                         "X-Correlation-ID": correlation_id},
            )
    except (httpx.HTTPError, ValueError) as exc:
        log("taskflow-backend", "Notification API request failed", level=logging.WARNING,
            error_type=type(exc).__name__, correlation_id=correlation_id, user_id=session.user_id)
    else:
        if result.status_code == 204:
            return Response(status_code=204)
        if result.status_code in {200, 404, 422}:
            with suppress(ValueError):
                return JSONResponse(result.json(), status_code=result.status_code)
        log("taskflow-backend", "Notification API returned unexpected response",
            level=logging.WARNING, correlation_id=correlation_id, user_id=session.user_id,
            upstream_status=result.status_code)
    raise ApiError(503, "NOTIFICATION_SERVICE_UNAVAILABLE", "Notifications temporarily unavailable")


@router.get("")
def list_notifications(
    request: Request, session: CurrentSession, page: int = 1, page_size: int = 20,
    is_read: bool | None = None, event_type: str | None = None, task_id: UUID | None = None,
):
    return forward(request, session)


@router.get("/unread-count")
def unread_count(request: Request, session: CurrentSession):
    return forward(request, session, "/unread-count")


@router.post("/read-all", status_code=204, dependencies=mutation)
def read_all(request: Request, session: CurrentSession):
    return forward(request, session, "/read-all")


@router.get("/{id}")
def get_notification(id: UUID, request: Request, session: CurrentSession):
    return forward(request, session, f"/{id}")


@router.patch("/{id}/read", dependencies=mutation)
def mark_read(id: UUID, request: Request, session: CurrentSession):
    return forward(request, session, f"/{id}/read")


@router.patch("/{id}/unread", dependencies=mutation)
def mark_unread(id: UUID, request: Request, session: CurrentSession):
    return forward(request, session, f"/{id}/unread")


@router.delete("/{id}", status_code=204, dependencies=mutation)
def delete_notification(id: UUID, request: Request, session: CurrentSession):
    return forward(request, session, f"/{id}")


@router.get("/{id}/deliveries")
def list_deliveries(id: UUID, request: Request, session: CurrentSession):
    return forward(request, session, f"/{id}/deliveries")

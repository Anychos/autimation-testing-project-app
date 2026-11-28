from secrets import compare_digest
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, Security
from fastapi.security import APIKeyHeader
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from notification_service.api_schemas import (
    DeliveryOut,
    ErrorOut,
    NotificationOut,
    NotificationPage,
    UnreadCount,
)
from notification_service.database import get_db, utcnow
from notification_service.errors import ApiError
from notification_service.events import EventType
from notification_service.models import Delivery, Notification
from notification_service.settings import get_settings

service_token = APIKeyHeader(name="X-Service-Token", auto_error=False)
Db = Annotated[Session, Depends(get_db)]
router = APIRouter(
    prefix="/api/v1/notifications", tags=["Notifications"],
    responses={code: {"model": ErrorOut} for code in (401, 404, 422, 503)},
)


def verified_user(
    token: Annotated[str | None, Security(service_token)],
    user_id: Annotated[str | None, Header(alias="X-User-ID")] = None,
) -> UUID:
    expected = get_settings().internal_service_token.get_secret_value()
    if not token or not compare_digest(token.encode(), expected.encode()):
        raise ApiError(401, "UNAUTHORIZED", "Invalid service credential")
    try:
        return UUID(user_id or "")
    except ValueError as exc:
        raise ApiError(422, "VALIDATION_ERROR", "X-User-ID must be a UUID") from exc


UserId = Annotated[UUID, Depends(verified_user)]


def scoped(user_id):
    return (Notification.user_id == user_id, Notification.deleted_at.is_(None))


def owned(db, id, user_id, *, lock=False):
    query = select(Notification).where(Notification.id == id, *scoped(user_id))
    notification = db.scalar(query.with_for_update() if lock else query)
    if notification is None:
        raise ApiError(404, "NOTIFICATION_NOT_FOUND", "Notification not found")
    return notification


@router.get("", response_model=NotificationPage)
def list_notifications(
    db: Db,
    user_id: UserId,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    is_read: bool | None = None,
    event_type: EventType | None = None,
    task_id: UUID | None = None,
):
    filters = list(scoped(user_id))
    if is_read is not None:
        filters.append(Notification.is_read == is_read)
    if event_type is not None:
        filters.append(Notification.event_type == event_type)
    if task_id is not None:
        filters.append(Notification.task_id == task_id)
    total = db.scalar(select(func.count()).select_from(Notification).where(*filters))
    offset = (page - 1) * page_size
    items = []
    if offset < total:
        items = db.scalars(
            select(Notification).where(*filters)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset(offset).limit(page_size)
        ).all()
    return NotificationPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/unread-count", response_model=UnreadCount)
def unread_count(db: Db, user_id: UserId):
    count = db.scalar(select(func.count()).select_from(Notification).where(
        *scoped(user_id), Notification.is_read.is_(False),
    ))
    return UnreadCount(count=count)


@router.post("/read-all", status_code=204)
def read_all(db: Db, user_id: UserId):
    db.execute(update(Notification).where(
        *scoped(user_id), Notification.is_read.is_(False),
    ).values(is_read=True, read_at=utcnow()))
    db.commit()
    return Response(status_code=204)


@router.get("/{id}", response_model=NotificationOut)
def get_notification(id: UUID, db: Db, user_id: UserId):
    return owned(db, id, user_id)


def set_read(db, id, user_id, read):
    notification = owned(db, id, user_id, lock=True)
    if notification.is_read != read:
        notification.is_read = read
        notification.read_at = utcnow() if read else None
    db.commit()
    return notification


@router.patch("/{id}/read", response_model=NotificationOut)
def mark_read(id: UUID, db: Db, user_id: UserId):
    return set_read(db, id, user_id, True)


@router.patch("/{id}/unread", response_model=NotificationOut)
def mark_unread(id: UUID, db: Db, user_id: UserId):
    return set_read(db, id, user_id, False)


@router.delete("/{id}", status_code=204)
def delete_notification(id: UUID, db: Db, user_id: UserId):
    notification = owned(db, id, user_id, lock=True)
    notification.deleted_at = utcnow()
    db.commit()
    return Response(status_code=204)


@router.get("/{id}/deliveries", response_model=list[DeliveryOut])
def list_deliveries(id: UUID, db: Db, user_id: UserId):
    notification = owned(db, id, user_id)
    return db.scalars(select(Delivery).where(
        Delivery.notification_id == notification.id
    ).order_by(Delivery.channel.desc())).all()

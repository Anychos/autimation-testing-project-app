import hashlib
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from notification_service.database import SessionLocal, utcnow
from notification_service.events import Event, TaskPayload
from notification_service.models import Delivery, Notification
from notification_service.settings import get_settings

CONTENT = {
    "user.registered": ("Welcome to TaskFlow!", "Your account has been successfully created."),
    "task.created": ("New task created", 'Your task "{title}" has been created successfully.'),
    "task.updated": ("Task updated", 'Your task "{title}" has been updated.'),
    "task.completed": ("Task completed", 'Congratulations! You have completed "{title}".'),
    "task.deleted": ("Task deleted", 'Your task "{title}" has been deleted.'),
}


class EventConflict(Exception):
    pass


def store_notification(event: Event) -> tuple[str, bool]:
    task = event.payload if isinstance(event.payload, TaskPayload) else None
    title, body = CONTENT[event.event_type]
    now = utcnow()
    digest = hashlib.sha256(event.model_dump_json().encode()).hexdigest()
    with SessionLocal.begin() as db:
        notification_id = db.scalar(
            insert(Notification).values(
                event_id=event.event_id, event_digest=digest, user_id=event.user_id,
                event_type=event.event_type, task_id=task.task_id if task else None,
                title=title, message=body.format(title=task.title if task else ""),
                created_at=now, event_occurred_at=event.occurred_at,
                correlation_id=event.correlation_id,
            ).on_conflict_do_nothing(index_elements=[Notification.event_id])
            .returning(Notification.id)
        )
        if notification_id is None:
            existing = db.scalars(select(Notification).where(
                Notification.event_id == event.event_id
            )).one()
            if existing.event_digest != digest:
                raise EventConflict
            return str(existing.id), False

        db.add(Delivery(
            notification_id=notification_id, channel="IN_APP", status="SENT", sent_at=now,
        ))
        recipient = getattr(event.payload, "recipient_email", None)
        if recipient and get_settings().email_enabled:
            delivery_id = uuid4()
            db.add(Delivery(
                id=delivery_id, notification_id=notification_id, channel="EMAIL",
                recipient=recipient, status="PENDING", next_attempt_at=now,
                message_id=f"<{delivery_id}@taskflow.test>",
            ))
        return str(notification_id), True

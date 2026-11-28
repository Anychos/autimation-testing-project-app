import json
import logging
from uuid import uuid4

from app.config import settings
from app.models import OutboxEvent, User, utcnow

EVENT_TYPES = ("user.registered", "task.created", "task.updated", "task.completed", "task.deleted")
logger = logging.getLogger("taskflow.events")


def log(service, message, *, level=logging.INFO, **fields):
    logger.log(level, json.dumps({
        "timestamp": utcnow().isoformat(), "level": logging.getLevelName(level),
        "service": service, "message": message, **fields,
    }, default=str))


def event_fields(event):
    return {
        "event_id": event.id, "correlation_id": event.correlation_id,
        "user_id": event.payload["user_id"],
        "task_id": event.payload["payload"].get("task_id"),
        "attempt_count": event.attempt_count, "event_type": event.event_type,
    }


def stage_event(db, event_type, user_id, correlation_id, payload):
    event_id = uuid4()
    now = utcnow()
    event = OutboxEvent(
        id=event_id, event_type=event_type, correlation_id=correlation_id,
        created_at=now, next_attempt_at=now, attempt_count=0,
        payload={
            "event_id": str(event_id), "event_type": event_type, "schema_version": 1,
            "occurred_at": now.isoformat(), "source": "taskflow-backend",
            "correlation_id": str(correlation_id), "user_id": str(user_id), "payload": payload,
        },
    )
    db.add(event)
    return event


def stage_task_event(db, event_type, task, correlation_id):
    if not settings.notifications_enabled:
        return None
    db.flush()
    payload = {"task_id": str(task.id), "title": task.title, "status": task.status}
    if event_type in {"task.created", "task.completed"}:
        payload["recipient_email"] = db.get(User, task.owner_id).email
    return stage_event(db, event_type, task.owner_id, correlation_id, payload)


def log_committed(event):
    if event is not None:
        log("taskflow-backend", "Outbox event created", **event_fields(event))

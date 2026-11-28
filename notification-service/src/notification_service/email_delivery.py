import logging
import smtplib
import ssl
from contextlib import closing
from datetime import timedelta
from email.headerregistry import Address
from email.message import EmailMessage
from html import escape
from importlib.resources import files
from time import perf_counter
from uuid import uuid4

from sqlalchemy import select, update

from notification_service.database import SessionLocal, utcnow
from notification_service.events import email_parts
from notification_service.logging_config import log
from notification_service.models import Delivery, Notification
from notification_service.settings import get_settings

TEMPLATES = files("notification_service").joinpath("templates")
PLAIN_TEMPLATE = TEMPLATES.joinpath("email.txt").read_text(encoding="utf-8")
HTML_TEMPLATE = TEMPLATES.joinpath("email.html").read_text(encoding="utf-8")


def build_email(delivery: Delivery, notification: Notification) -> EmailMessage:
    settings = get_settings()
    message = EmailMessage()
    sender, sender_domain = email_parts(settings.smtp_from_email)
    recipient, recipient_domain = email_parts(delivery.recipient)
    message["From"] = Address(settings.smtp_from_name, sender, sender_domain)
    message["To"] = Address(username=recipient, domain=recipient_domain)
    message["Subject"] = notification.title
    message["Message-ID"] = delivery.message_id
    message["X-Event-ID"] = str(notification.event_id)
    message["X-Correlation-ID"] = str(notification.correlation_id)
    message["X-Notification-ID"] = str(notification.id)
    if notification.task_id:
        message["X-Task-ID"] = str(notification.task_id)
    fields = {
        "title": notification.title, "message": notification.message,
        "task": f"Task ID: {notification.task_id}" if notification.task_id else "",
        "occurred_at": notification.event_occurred_at.isoformat(),
    }
    message.set_content(PLAIN_TEMPLATE.format(**fields))
    message.add_alternative(
        HTML_TEMPLATE.format(**{key: escape(value) for key, value in fields.items()}),
        subtype="html",
    )
    return message


def send_email(delivery: Delivery, notification: Notification):
    settings = get_settings()
    message = build_email(delivery, notification)
    options = {"host": settings.smtp_host, "port": settings.smtp_port,
               "timeout": settings.smtp_timeout}
    if settings.smtp_use_ssl:
        smtp = smtplib.SMTP_SSL(**options, context=ssl.create_default_context())
    else:
        smtp = smtplib.SMTP(**options)
    with closing(smtp):
        if settings.smtp_use_tls:
            smtp.starttls(context=ssl.create_default_context())
        smtp.send_message(message)


def claim_delivery():
    settings = get_settings()
    now = utcnow()
    with SessionLocal.begin() as db:
        row = db.execute(
            select(Delivery, Notification).join(Notification)
            .where(
                Delivery.channel == "EMAIL",
                Delivery.status.in_(["PENDING", "RETRYING", "PROCESSING"]),
                Delivery.next_attempt_at <= now,
            )
            .order_by(Delivery.next_attempt_at, Delivery.id)
            .limit(1)
            .with_for_update(of=Delivery, skip_locked=True)
        ).first()
        if row is None:
            return None
        delivery, notification = row
        if delivery.attempt_count >= settings.email_max_retries + 1:
            delivery.status = "FAILED"
            delivery.last_error = "Delivery lease expired or retry budget exhausted"
            delivery.next_attempt_at = None
            delivery.lease_id = None
        else:
            delivery.status = "PROCESSING"
            delivery.attempt_count += 1
            delivery.lease_id = uuid4()
            delivery.next_attempt_at = now + timedelta(seconds=12 * settings.smtp_timeout + 30)
        return delivery, notification


def process_delivery() -> bool:
    claimed = claim_delivery()
    if claimed is None:
        return False
    delivery, notification = claimed
    fields = {
        "event_id": notification.event_id, "correlation_id": notification.correlation_id,
        "notification_id": notification.id, "task_id": notification.task_id,
        "user_id": notification.user_id, "attempt_count": delivery.attempt_count,
    }
    metrics = None
    if get_settings().metrics_enabled:
        from notification_service import worker_metrics as metrics

    if delivery.status == "FAILED":
        if metrics:
            metrics.SMTP.labels("failed").inc()
        log("notification-worker", "SMTP delivery exhausted", level=logging.WARNING, **fields)
        return True

    settings = get_settings()
    now = utcnow()
    started = perf_counter()
    if metrics:
        metrics.SMTP.labels("attempt").inc()
        if delivery.attempt_count > 1:
            metrics.SMTP.labels("retry").inc()
    try:
        send_email(delivery, notification)
    except (OSError, smtplib.SMTPException, ValueError) as exc:
        retry = delivery.attempt_count <= settings.email_max_retries
        status = "RETRYING" if retry else "FAILED"
        sent_at = None
        next_attempt = (
            utcnow() + timedelta(seconds=settings.email_retry_interval_seconds) if retry else None
        )
        error = type(exc).__name__
    else:
        status, sent_at, next_attempt, error = "SENT", utcnow(), None, None

    if metrics:
        metrics.SMTP_DURATION.observe(perf_counter() - started)
        if sent_at:
            metrics.SMTP.labels("accepted").inc()
            lag = (sent_at - notification.event_occurred_at).total_seconds()
            metrics.SMTP_LAG.observe(max(0, lag))
        else:
            metrics.SMTP.labels("error").inc()

    with SessionLocal.begin() as db:
        result = db.execute(update(Delivery).where(
            Delivery.id == delivery.id, Delivery.lease_id == delivery.lease_id,
        ).values(
            status=status, sent_at=sent_at, next_attempt_at=next_attempt,
            last_error=error, lease_id=None,
        ))
    if metrics and result.rowcount and status == "FAILED":
        metrics.SMTP.labels("failed").inc()
    log(
        "notification-worker", "SMTP delivery attempt",
        level=logging.WARNING if error or not result.rowcount else logging.INFO,
        status=status, error_type=error, lease_current=bool(result.rowcount),
        duration_seconds=round((utcnow() - now).total_seconds(), 3), **fields,
    )
    return True

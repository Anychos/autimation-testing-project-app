import json
import logging
import signal
import sys
from time import perf_counter
from contextlib import suppress
from datetime import timedelta
from threading import Event

import pika
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database import SessionLocal, engine
from app.models import OutboxEvent, utcnow
from app.outbox import EVENT_TYPES, event_fields, log

SERVICE = "taskflow-outbox-publisher"
BROKER_ERRORS = (pika.exceptions.AMQPError, OSError)


class Publisher:
    def __init__(self):
        self.connection = None
        self.channel = None

    def close(self):
        if self.connection is not None and self.connection.is_open:
            with suppress(*BROKER_ERRORS):
                self.connection.close()
        self.channel = self.connection = None

    def connect(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=settings.rabbitmq_host, port=settings.rabbitmq_port,
            virtual_host=settings.rabbitmq_vhost,
            credentials=pika.PlainCredentials(
                settings.rabbitmq_user, settings.rabbitmq_password.get_secret_value(),
            ),
            heartbeat=15, socket_timeout=3, stack_timeout=5, blocked_connection_timeout=5,
        ))
        channel = self.connection.channel()
        channel.exchange_declare(settings.rabbitmq_exchange, exchange_type="topic", durable=True)
        channel.queue_declare(settings.rabbitmq_queue, durable=True)
        for key in EVENT_TYPES:
            channel.queue_bind(settings.rabbitmq_queue, settings.rabbitmq_exchange, key)
        channel.confirm_delivery()
        self.channel = channel
        log(SERVICE, "RabbitMQ publisher connected")

    def publish(self, event):
        if self.channel is None:
            self.connect()
        self.channel.basic_publish(
            settings.rabbitmq_exchange, event.event_type,
            json.dumps(event.payload).encode(), mandatory=True,
            properties=pika.BasicProperties(
                content_type="application/json", delivery_mode=2,
                message_id=str(event.id), correlation_id=str(event.correlation_id),
            ),
        )


def publish_one(publisher):
    started = perf_counter() if settings.metrics_enabled else None
    with SessionLocal.begin() as db:
        event = db.scalar(
            select(OutboxEvent)
            .where(OutboxEvent.status == "PENDING", OutboxEvent.next_attempt_at <= utcnow())
            .order_by(OutboxEvent.created_at, OutboxEvent.id)
            .limit(1).with_for_update(skip_locked=True)
        )
        if event is None:
            return False
        event.attempt_count += 1
        try:
            publisher.publish(event)
        except BROKER_ERRORS as exc:
            publisher.close()
            event.last_error = type(exc).__name__
            event.next_attempt_at = utcnow() + timedelta(
                seconds=min(30, 2 ** min(event.attempt_count, 5)),
            )
        else:
            event.status = "PUBLISHED"
            event.published_at = utcnow()
            if started is not None:
                from app.outbox_metrics import observe_confirmation

                observe_confirmation(event, event.published_at)
            event.last_error = None

    if started is not None:
        from app.outbox_metrics import observe_publish

        observe_publish(event, perf_counter() - started)
    if event.status == "PUBLISHED":
        log(SERVICE, "Outbox event published", **event_fields(event))
    else:
        log(SERVICE, "Outbox publication failed", level=logging.WARNING,
            error_type=event.last_error, **event_fields(event))
    return True


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    logging.getLogger("pika").setLevel(logging.CRITICAL)
    stop = Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    if not settings.notifications_enabled:
        log(SERVICE, "Notifications disabled")
        stop.wait()
        return
    if settings.metrics_enabled:
        from app.outbox_metrics import start_metrics

        start_metrics()
    publisher = Publisher()
    try:
        while not stop.is_set():
            try:
                if publisher.connection is not None:
                    publisher.connection.process_data_events(time_limit=0)
                for _ in range(settings.outbox_batch_size):
                    if stop.is_set():
                        break
                    if not publish_one(publisher):
                        stop.wait(settings.outbox_poll_interval)
                        break
            except BROKER_ERRORS as exc:
                publisher.close()
                log(SERVICE, "RabbitMQ disconnected", level=logging.WARNING,
                    error_type=type(exc).__name__)
                stop.wait(2)
            except SQLAlchemyError as exc:
                log(SERVICE, "Outbox database error", level=logging.WARNING,
                    error_type=type(exc).__name__)
                stop.wait(2)
    finally:
        publisher.close()
        engine.dispose()


if __name__ == "__main__":
    main()
